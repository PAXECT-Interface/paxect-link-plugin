#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link Plugin — Demo 04: Overhead Guard / Fail-Safe Sequence
v1.3.2
"""
import os, sys, time, json, tempfile, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parent.parent
LINK = REPO / "paxect_link_plugin.py"
CORE = REPO / "paxect_core.py"

def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1<<16), b""): h.update(c)
    return h.hexdigest()

def main():
    print(f"[Demo04] {now_utc()} — starting Link Overhead-Guard test")

    base = Path(tempfile.gettempdir()) / f"paxect_demo04_{os.getpid()}"
    inbox, outbox = base/"inbox", base/"outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)

    # maak 5 testbestanden (verschillende groottes)
    for i in range(5):
        data = os.urandom(256*(i+1))
        (inbox / f"test_{i+1}.bin").write_bytes(data)

    env = os.environ.copy()
    env["PAXECT_CORE_PATH"] = str(CORE)
    env["PAXECT_NODE"] = "OverheadGuard"

    proc = subprocess.Popen(
        [sys.executable, str(LINK), "--inbox", str(inbox), "--outbox", str(outbox)],
        env=env,
    )

    time.sleep(5)
    proc.terminate()

    # Resultaten analyseren
    relayed = list(outbox.glob("*.freq"))
    print(f"[Demo04] Relayed files : {len(relayed)}")
    for f in relayed:
        print(f" - {f.name} ({sha256(f)[:12]})")

    # Check logs
    log_path = REPO / "paxect_link_log.jsonl"
    if log_path.exists():
        lines = log_path.read_text().splitlines()[-5:]
        print("[Demo04] Last 5 log lines:")
        for ln in lines: print(ln)
    else:
        print("[Demo04] No log found.")

    print(f"[Demo04] {now_utc()} — finished Link Overhead-Guard test ✅")

if __name__ == "__main__":
    main()
