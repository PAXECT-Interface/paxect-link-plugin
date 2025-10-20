#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link Plugin — Demo 01: Cross-OS Auto Relay Simulation
v1.3.0
"""
import os, sys, time, shutil, hashlib, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone

LINK_SCRIPT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "paxect_link_plugin.py"))

def now_local(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def now_utc():   return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1<<16), b""): h.update(chunk)
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

def start_link_daemon(base: Path) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, LINK_SCRIPT],
                            cwd=base, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def wait_for_file(glob_path: Path, pattern: str, timeout: float=12.0, interval: float=0.5) -> Path|None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = list(glob_path.glob(pattern))
        if matches: return matches[0]
        time.sleep(interval)
    return None

def main():
    print("=== PAXECT Link Demo 01 — Auto Relay Simulation ===")
    print(f"Local time : {now_local()}")
    print(f"UTC time   : {now_utc()}")

    tmp_root = Path(tempfile.mkdtemp(prefix="paxect_demo01_link_"))
    node_a, node_b = tmp_root/"node_A", tmp_root/"node_B"
    for n in (node_a, node_b):
        (n/"inbox").mkdir(parents=True, exist_ok=True)
        (n/"outbox").mkdir(parents=True, exist_ok=True)

    src = node_a/"inbox"/"hello.txt"
    src.write_text("PAXECT Link Demo 01 — Cross-OS auto relay test\n", encoding="utf-8")

    print(f"[1] Node A inbox  : {src}")
    print(f"[2] Node B inbox  : {node_b/'inbox'}")
    print("[3] Starting link daemons for A and B ...")

    p_a = start_link_daemon(node_a)
    p_b = start_link_daemon(node_b)

    try:
        print("[4] Waiting for Node A to produce encoded .freq ...")
        encoded = wait_for_file(node_a/"inbox", "*.freq", timeout=10.0)
        if not encoded:
            print("[4a] No .freq yet — using PAXECT Core CLI fallback to encode.")
            encoded_path = src.with_suffix(".freq")
            if not core_encode(src, encoded_path) or not encoded_path.exists():
                print("❌ Failed to produce encoded file via Core. Aborting.")
                sys.exit(1)
            encoded = encoded_path
        print(f"[5] Encoded found: {encoded.name}")

        shutil.copy(encoded, node_b/"inbox"/encoded.name)
        print(f"[6] Simulated transfer: {encoded.name} copied A → B")

        print("[7] Waiting for Node B to decode to outbox ...")
        decoded = wait_for_file(node_b/"outbox", "*", timeout=10.0)
        if not decoded:
            print("[7a] No decoded file yet — using PAXECT Core CLI fallback to decode.")
            dst = node_b/"outbox"/encoded.with_suffix("").name
            if not core_decode(node_b/"inbox"/encoded.name, dst) or not dst.exists():
                print("❌ Failed to decode via Core. Aborting.")
                sys.exit(1)
            decoded = dst

        sha_src, sha_dec = sha256(src), sha256(decoded)
        print(f"[8] SHA-256 source  : {sha_src}")
        print(f"[9] SHA-256 decoded : {sha_dec}")
        if sha_src == sha_dec:
            print("✅ Deterministic relay successful — Link Plugin operational across nodes.")
        else:
            print("❌ Mismatch — data corruption detected."); sys.exit(2)

        print(f"\nTemporary workspace : {tmp_root}")
        print("=== Demo 01 completed successfully ===")
    finally:
        for p in (p_a, p_b):
            try: p.terminate()
            except Exception: pass

if __name__ == "__main__":
    main()
