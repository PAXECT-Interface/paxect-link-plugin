#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link Plugin — Demo 02: Live Relay Monitor
v1.0.0

Starts one Link node, generates traffic, and live-monitors:
- inbox/outbox changes
- JSONL audit log (paxect_link_log.jsonl)
- fallback to PAXECT Core CLI when the daemon does not process in time

No external dependencies. Fully offline and deterministic.
"""

import os
import sys
import time
import json
import hashlib
import tempfile
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timezone

LINK_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "paxect_link_plugin.py"))

# ---------- Small utils ----------
def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def find_core_cmd() -> list[str] | None:
    repo_root = Path(__file__).resolve().parent.parent
    candidate_py = repo_root / "paxect_core.py"
    if candidate_py.exists():
        return [sys.executable, str(candidate_py)]
    return ["paxect_core"]

def core_encode(src: Path, dst: Path) -> bool:
    cmd = find_core_cmd()
    try:
        subprocess.run(cmd + ["encode", "-i", str(src), "-o", str(dst)],
                       check=True, capture_output=True)
        return True
    except Exception:
        return False

def core_decode(src: Path, dst: Path) -> bool:
    cmd = find_core_cmd()
    try:
        subprocess.run(cmd + ["decode", "-i", str(src), "-o", str(dst)],
                       check=True, capture_output=True)
        return True
    except Exception:
        return False

# ---------- Live log tailer ----------
def tail_jsonl(logfile: Path, stop_evt: threading.Event):
    print(f"[MON] Tail log: {logfile}")
    seen_size = 0
    while not stop_evt.is_set():
        try:
            if logfile.exists():
                size = logfile.stat().st_size
                if size > seen_size:
                    with logfile.open("r", encoding="utf-8") as f:
                        f.seek(seen_size)
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                obj = json.loads(line)
                                evt = obj.get("event")
                                src = obj.get("src")
                                dst = obj.get("dst")
                                status = obj.get("status")
                                ts = obj.get("datetime_utc")
                                msg = obj.get("message")
                                print(f"[LOG] {ts} | {evt:<12} | {status:<7} | src={src} dst={dst} {('|' if msg else '')} {msg or ''}")
                            except json.JSONDecodeError:
                                print(f"[LOG][WARN] non-JSON line: {line[:120]}")
                    seen_size = size
        except Exception as e:
            print(f"[MON][ERR] tail error: {e}")
        time.sleep(0.25)

# ---------- Dir monitor ----------
def monitor_dirs(inbox: Path, outbox: Path, stop_evt: threading.Event):
    prev_in = set()
    prev_out = set()
    while not stop_evt.is_set():
        try:
            cur_in = set(p.name for p in inbox.glob("*") if p.is_file())
            cur_out = set(p.name for p in outbox.glob("*") if p.is_file())

            new_in = cur_in - prev_in
            gone_in = prev_in - cur_in
            new_out = cur_out - prev_out
            gone_out = prev_out - cur_out

            if new_in:
                print(f"[MON] inbox+  : {sorted(new_in)}")
            if gone_in:
                print(f"[MON] inbox-  : {sorted(gone_in)}")
            if new_out:
                print(f"[MON] outbox+ : {sorted(new_out)}")
            if gone_out:
                print(f"[MON] outbox- : {sorted(gone_out)}")

            prev_in, prev_out = cur_in, cur_out
        except Exception as e:
            print(f"[MON][ERR] dir error: {e}")
        time.sleep(0.5)

# ---------- Traffic generator ----------
def generate_traffic(inbox: Path):
    print("[GEN] Creating sample files in inbox ...")
    for i in range(1, 4):
        p = inbox / f"sample_{i:02d}.txt"
        p.write_text(f"PAXECT Link Demo 02 — sample {i}\n", encoding="utf-8")
        print(f"[GEN] + {p.name}")
        time.sleep(0.5)

# ---------- Wait helpers ----------
def wait_for_encoded(inbox: Path, timeout=6.0) -> bool:
    """Wait until at least one *.freq appears (daemon encode), else False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(inbox.glob("*.freq")):
            return True
        time.sleep(0.5)
    return False

def force_encode_if_needed(inbox: Path):
    # Encode any non-.freq files with Core fallback
    for p in list(inbox.iterdir()):
        if p.is_file() and p.suffix != ".freq":
            dst = p.with_suffix(".freq")
            if dst.exists():
                continue
            print(f"[FALLBACK] Core encode: {p.name} -> {dst.name}")
            if core_encode(p, dst):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass

def wait_for_decoded(outbox: Path, expect_count: int, timeout=8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        cnt = len([p for p in outbox.iterdir() if p.is_file()])
        if cnt >= expect_count:
            return True
        time.sleep(0.5)
    return False

def force_decode_if_needed(inbox: Path, outbox: Path):
    # Decode any *.freq that linger with Core fallback
    for f in list(inbox.glob("*.freq")):
        dst = outbox / f.with_suffix("").name
        if dst.exists():
            continue
        print(f"[FALLBACK] Core decode: {f.name} -> {dst.name}")
        if core_decode(f, dst):
            try:
                f.unlink(missing_ok=True)
            except Exception:
                pass

# ---------- Main demo ----------
def main():
    print("=== PAXECT Link Demo 02 — Live Relay Monitor ===")
    print(f"Local time : {now_local()}")
    print(f"UTC time   : {now_utc()}")

    tmp_root = Path(tempfile.mkdtemp(prefix="paxect_demo02_link_"))
    node = tmp_root / "node_live"
    inbox = node / "inbox"
    outbox = node / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    print(f"[SETUP] Node dir : {node}")
    print(f"[SETUP] inbox    : {inbox}")
    print(f"[SETUP] outbox   : {outbox}")

    # Start link daemon
    print("[RUN] Starting link daemon ...")
    proc = subprocess.Popen([sys.executable, LINK_SCRIPT], cwd=node,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Start monitors
    stop_evt = threading.Event()
    log_file = node / "paxect_link_log.jsonl"
    t1 = threading.Thread(target=tail_jsonl, args=(log_file, stop_evt), daemon=True)
    t2 = threading.Thread(target=monitor_dirs, args=(inbox, outbox, stop_evt), daemon=True)
    t1.start(); t2.start()

    try:
        # Generate test traffic
        generate_traffic(inbox)

        # Wait for encode; fallback if needed
        if not wait_for_encoded(inbox, timeout=6.0):
            print("[MON] No encoded files yet — forcing Core encode fallback.")
            force_encode_if_needed(inbox)

        # Wait a bit for daemon decode; fallback if needed
        if not wait_for_decoded(outbox, expect_count=3, timeout=8.0):
            print("[MON] Expected decoded files not found — forcing Core decode fallback.")
            force_decode_if_needed(inbox, outbox)

        # Verify integrity of all outputs (deterministic round-trip)
        print("[VER] Verifying SHA-256 of decoded files ...")
        ok = True
        for i in range(1, 4):
            src = f"PAXECT Link Demo 02 — sample {i}\n".encode("utf-8")
            src_sha = hashlib.sha256(src).hexdigest()

            # Find decoded file content
            # Each decoded file should be named sample_XX (no suffix)
            target = outbox / f"sample_{i:02d}"
            if not target.exists():
                print(f"[VER][ERR] Missing decoded: {target.name}")
                ok = False
                continue
            dec_sha = sha256(target)
            # Because the decoded file is reconstructed from encoded, content should match the original text
            # NOTE: The original plaintext is not saved to disk, we compare by hash of expected content.
            if dec_sha != src_sha:
                print(f"[VER][ERR] SHA mismatch: {target.name}")
                ok = False
            else:
                print(f"[VER] OK  {target.name}  sha256={dec_sha}")

        if ok:
            print("✅ Live relay verified — deterministic and operational.")
        else:
            print("❌ Some files failed verification.")
            sys.exit(2)

        print(f"\nTemporary workspace : {tmp_root}")
        print("=== Demo 02 completed successfully ===")

    finally:
        stop_evt.set()
        try:
            proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
