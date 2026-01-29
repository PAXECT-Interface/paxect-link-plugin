#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link Plugin — Deterministic Cross-System Relay
v1.2.0 (enterprise, hardened, stdlib-only)

Purpose
-------
Deterministic, offline file relay between runtimes/systems within the PAXECT
ecosystem. Zero telemetry. Local-only. Plug-and-play.

Key hardening
-------------
- Cross-OS support (uses `platform`, no `os.uname` dependency)
- Single-instance lock (atomic lockfile) to prevent duplicate processes
- Atomic I/O (.part → fsync → rename) for crash-safe writes
- Path safety: block traversal outside inbox; skip hidden/partial files
- Policy enforcement: extension allowlist, max file size, trusted nodes
- Sidecar checksums: write `.freq.sha256` on encode; verify before decode
- Optional manifest trust via HMAC (env: PAXECT_LINK_HMAC_KEY; policy require_sig)
- JSONL logging with size-based rotation and log levels
- Backoff on encode/decode failures
- Deterministic peer discovery via local manifests

Environment variables
---------------------
PAXECT_LINK_INBOX, PAXECT_LINK_OUTBOX, PAXECT_LINK_POLICY, PAXECT_LINK_MANIFEST,
PAXECT_LINK_LOG, PAXECT_LINK_LOCK, PAXECT_CORE, PAXECT_LINK_POLL_SEC,
PAXECT_LINK_BACKOFF_SEC, PAXECT_LINK_LOG_MAX, PAXECT_LINK_HMAC_KEY

External dependencies
---------------------
None (Python standard library only). Encoding/decoding is delegated to a
“PAXECT Core” CLI pointed to by PAXECT_CORE (e.g., "python3 paxect_core.py").

Quick start
-----------
export PAXECT_CORE="python3 paxect_core.py"
python3 paxect_link_plugin.py
"""

from __future__ import annotations
import os
import json
import time
import hmac
import hashlib
import subprocess
import signal
import platform
from pathlib import Path
from datetime import datetime

# ====== Configuration (env overrides) ======
INBOX      = Path(os.environ.get("PAXECT_LINK_INBOX" , "inbox"))
OUTBOX     = Path(os.environ.get("PAXECT_LINK_OUTBOX", "outbox"))
CONFIG     = Path(os.environ.get("PAXECT_LINK_POLICY", "link_policy.json"))
MANIFEST   = Path(os.environ.get("PAXECT_LINK_MANIFEST", "link_manifest.json"))
LOGFILE    = Path(os.environ.get("PAXECT_LINK_LOG", "paxect_link_log.jsonl"))
LOCKFILE   = Path(os.environ.get("PAXECT_LINK_LOCK", ".paxect_link.lock"))

# PAXECT Core CLI (encode/decode). Example: "python3 paxect_core.py"
PAXECT_CORE = os.environ.get("PAXECT_CORE", "python3 paxect_core.py").split()

POLL_INTERVAL = float(os.environ.get("PAXECT_LINK_POLL_SEC", "2.0"))
BACKOFF_SEC   = float(os.environ.get("PAXECT_LINK_BACKOFF_SEC", "5.0"))
LOG_MAX_BYTES = int(os.environ.get("PAXECT_LINK_LOG_MAX", str(5 * 1024 * 1024)))  # 5MB
VERSION = "1.2.0"

# Default policy (written if missing)
DEFAULT_POLICY = {
    "version": VERSION,
    "trusted_nodes": ["localhost"],
    "allowed_suffixes": [".bin", ".txt", ".json", ".csv", ".aead", ".freq"],
    "max_file_mb": 256,
    "require_sig": False,   # set True to require HMAC-signed manifests
    "auto_delete": True,
    "log_level": "info"     # debug | info | warn | error
}

# Internal state
HMAC_KEY = os.environ.get("PAXECT_LINK_HMAC_KEY", "")
HMAC_KEY_BYTES = HMAC_KEY.encode("utf-8") if HMAC_KEY else None
_running = True

# ====== Utilities ======
def utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def _level_val(level: str) -> int:
    return {"debug": 10, "info": 20, "warn": 30, "error": 40}.get(level, 20)

def _should_log(cfg: dict, level: str) -> bool:
    return _level_val(level) >= _level_val(cfg.get("log_level", "info"))

def _rotate_log_if_needed():
    try:
        if LOGFILE.exists() and LOGFILE.stat().st_size > LOG_MAX_BYTES:
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            LOGFILE.rename(LOGFILE.with_name(f"{LOGFILE.stem}.{ts}.jsonl"))
    except Exception:
        # never fail on rotation
        pass

def log_event(cfg: dict, level: str, event: str,
              src: Path | str | None = None,
              dst: Path | str | None = None,
              status: str = "ok", msg: str | None = None):
    """Structured JSONL logging with levels and rotation."""
    if not _should_log(cfg, level):
        return
    _rotate_log_if_needed()
    entry = {
        "datetime_utc": utc_now(),
        "level": level,
        "event": event,
        "src": str(src) if src else None,
        "dst": str(dst) if dst else None,
        "status": status,
        "message": msg,
        "version": VERSION,
    }
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def sha256_file(path: Path) -> str:
    """Streaming SHA-256 (1 MiB chunks)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def safe_relative(child: Path, parent: Path) -> bool:
    """Return True if child is within parent (after resolve())."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False

def is_hidden(p: Path) -> bool:
    """Skip hidden/partial/temp files."""
    return p.name.startswith(".") or p.name.endswith(".part") or p.name.endswith(".tmp")

# ====== Policy ======
def ensure_policy():
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(DEFAULT_POLICY, indent=2))
        print(f"[LINK] Wrote default policy: {CONFIG}")

def load_policy() -> dict:
    cfg = load_json(CONFIG, DEFAULT_POLICY)
    # normalize suffixes to ".ext"
    cfg["allowed_suffixes"] = list({s if s.startswith(".") else f".{s}"
                                    for s in cfg.get("allowed_suffixes", [])})
    return cfg

def policy_allows(cfg: dict, node: str, file_path: Path) -> tuple[bool, str]:
    """Enforce: trusted node, allowed extension, max size."""
    if node not in cfg.get("trusted_nodes", []):
        return False, f"untrusted_node:{node}"
    if file_path.suffix not in set(cfg.get("allowed_suffixes", [])):
        return False, f"disallowed_suffix:{file_path.suffix}"
    try:
        max_mb = int(cfg.get("max_file_mb", 256))
    except Exception:
        max_mb = 256
    if file_path.exists() and file_path.stat().st_size > max_mb * 1024 * 1024:
        return False, f"file_too_large:{file_path.stat().st_size}B"
    return True, "ok"

# ====== Manifest (optional HMAC) ======
def _manifest_payload() -> dict:
    return {
        "datetime_utc": utc_now(),
        "node": platform.node() or "localhost",
        "platform": platform.system(),
        "policy": CONFIG.name,
        "inbox": str(INBOX.resolve()),
        "outbox": str(OUTBOX.resolve()),
        "version": VERSION,
    }

def _sign_dict(d: dict) -> str:
    if not HMAC_KEY_BYTES:
        return ""
    body = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(HMAC_KEY_BYTES, body, hashlib.sha256).hexdigest()

def write_manifest(cfg: dict):
    payload = _manifest_payload()
    sig = _sign_dict(payload)
    manifest = {"payload": payload, "hmac_sha256": sig}
    tmp = MANIFEST.with_suffix(MANIFEST.suffix + ".part")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(MANIFEST)

def verify_manifest(cfg: dict, obj: dict) -> bool:
    """True if manifest is acceptable; with require_sig=True, HMAC must match."""
    if not cfg.get("require_sig", False):
        return True
    if not HMAC_KEY_BYTES:
        return False
    payload = obj.get("payload", {})
    expect = _sign_dict(payload)
    return hmac.compare_digest(expect, obj.get("hmac_sha256", ""))

# ====== Single-instance lock ======
def take_lock():
    """Atomic create; raises FileExistsError if lock already present."""
    fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w") as f:
        f.write(f"{os.getpid()}\n")

def release_lock():
    try:
        LOCKFILE.unlink(missing_ok=True)
    except Exception:
        pass

# ====== I/O helpers ======
def atomic_write(dst: Path, data: bytes):
    """Write to .part, fsync, rename → crash-safe."""
    tmp = dst.with_suffix(dst.suffix + ".part")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(dst)

def run_core(cfg: dict, args: list[str]) -> tuple[bool, str]:
    """Invoke PAXECT Core, return (ok, text)."""
    try:
        res = subprocess.run(PAXECT_CORE + args, check=True, capture_output=True)
        return True, res.stdout.decode("utf-8", "replace")
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode("utf-8", "replace")

# ====== Checksum gate ======
def verify_sidecar_checksum(freq: Path) -> bool:
    """
    Verify sidecar SHA-256 for a .freq.
    Missing sidecar → True (compatibility). Bad value → False.
    """
    side = freq.with_suffix(freq.suffix + ".sha256")
    if not side.exists():
        return True
    try:
        want = side.read_text(encoding="ascii").strip()
        have = sha256_file(freq)
        return hmac.compare_digest(want, have)
    except Exception:
        return False

# ====== Encode / Decode ======
def encode_file(cfg: dict, src: Path):
    """
    Encode a source file to .freq via PAXECT Core.
    Write sidecar .freq.sha256. Delete source if auto_delete=True.
    """
    dst = src.with_suffix(".freq")
    if dst.exists():
        return
    ok, out = run_core(cfg, ["encode", "-i", str(src), "-o", str(dst)])
    if ok:
        sha = sha256_file(dst)
        atomic_write(dst.with_suffix(dst.suffix + ".sha256"), (sha + "\n").encode("ascii"))
        log_event(cfg, "info", "encode", src, dst, msg=f"sha256={sha}")
        if cfg.get("auto_delete", True):
            try:
                src.unlink(missing_ok=True)
            except Exception:
                pass
    else:
        log_event(cfg, "error", "encode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)

def decode_file(cfg: dict, src: Path):
    """
    Decode a .freq into outbox/<name without extension>.
    Block on sidecar mismatch. Delete source + sidecar if auto_delete=True.
    """
    dst = OUTBOX / src.with_suffix("").name
    if dst.exists():
        return
    if not verify_sidecar_checksum(src):
        log_event(cfg, "error", "checksum_mismatch", src, status="error", msg="sidecar sha256 mismatch")
        return
    ok, out = run_core(cfg, ["decode", "-i", str(src), "-o", str(dst)])
    if ok:
        sha = sha256_file(dst)
        log_event(cfg, "info", "decode", src, dst, msg=f"sha256={sha}")
        if cfg.get("auto_delete", True):
            try:
                src.unlink(missing_ok=True)
                src.with_suffix(src.suffix + ".sha256").unlink(missing_ok=True)
            except Exception:
                pass
    else:
        log_event(cfg, "error", "decode_error", src, status="error", msg=out)
        time.sleep(BACKOFF_SEC)

# ====== Peer handshake ======
def handshake(cfg: dict):
    """
    Deterministic discovery: read *.json manifests in current directory.
    With require_sig=True, unsigned/invalid manifests are rejected.
    """
    peers = 0
    for m in Path(".").glob("link_manifest*.json"):
        if m.resolve() == MANIFEST.resolve():
            continue
        try:
            obj = json.loads(m.read_text(encoding="utf-8"))
            if verify_manifest(cfg, obj):
                peer = obj.get("payload", {})
                node = peer.get("node", "unknown")
                plat = peer.get("platform")
                log_event(cfg, "info", "handshake", m.name, msg=f"peer={node}")
                print(f"[LINK] Peer: {node} ({plat})")
                peers += 1
            else:
                log_event(cfg, "warn", "handshake_reject", m.name, status="warn", msg="bad_sig")
        except Exception as e:
            log_event(cfg, "warn", "handshake_parse_error", m.name, status="warn", msg=str(e))
    if peers == 0:
        log_event(cfg, "debug", "handshake_none", msg="no peers found")

# ====== Signals ======
def _sigterm(_sig, _frm):
    global _running
    _running = False

# ====== Main ======
def main():
    print(f"=== PAXECT Link Plugin — Enterprise Relay v{VERSION} ===")
    # Print script path for sanity when multiple copies exist
    print(f"Script path: {Path(__file__).resolve()}")
    print(f"Local time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"UTC time   : {utc_now()}")
    print(f"Inbox      : {INBOX.resolve()}")
    print(f"Outbox     : {OUTBOX.resolve()}")
    print(f"Policy     : {CONFIG.resolve()}")
    print(f"Log file   : {LOGFILE.resolve()}\n")

    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    ensure_policy()
    cfg = load_policy()

    # Single-instance lock
    try:
        take_lock()
    except FileExistsError:
        print("[LINK] Another instance is running (lock exists). Exiting.")
        return

    # Graceful shutdown
    signal.signal(signal.SIGINT, _sigterm)
    signal.signal(signal.SIGTERM, _sigterm)

    try:
        write_manifest(cfg)
        handshake(cfg)
        log_event(cfg, "info", "startup", INBOX.resolve(), OUTBOX.resolve(), msg=f"poll={POLL_INTERVAL}s")
        print("[LINK] Watching for deterministic file relay... (Ctrl+C to stop)\n")

        node = platform.node() or "localhost"

        while _running:
            # Refresh manifest deterministically per poll (discovery)
            write_manifest(cfg)

            for f in INBOX.iterdir():
                if not f.is_file():
                    continue
                if is_hidden(f):
                    continue
                if not safe_relative(f, INBOX):
                    log_event(cfg, "warn", "path_outside_inbox", f, status="warn")
                    continue

                allowed, reason = policy_allows(cfg, node, f)
                if not allowed:
                    log_event(cfg, "warn", "policy_block", f, status="warn", msg=reason)
                    continue

                if f.suffix == ".freq":
                    decode_file(cfg, f)
                else:
                    encode_file(cfg, f)

            time.sleep(POLL_INTERVAL)

        print("\n[LINK] Stopping…")

    finally:
        log_event(cfg, "info", "shutdown", status="ok")
        release_lock()

if __name__ == "__main__":
    main()
