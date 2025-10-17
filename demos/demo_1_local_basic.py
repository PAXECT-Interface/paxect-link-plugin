#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link — Demo 1: Local Basic Relay Test (enterprise)
Purpose: sanity-check local encode→decode via PAXECT Core + Link Plugin.
"""

import os, time, hashlib, subprocess, tempfile, signal, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = ROOT / "paxect_link_plugin.py"
CORE = ROOT / "paxect_core.py"

TMP = Path(tempfile.gettempdir())
INBOX = TMP / "paxect_demo1_inbox"
OUTBOX = TMP / "paxect_demo1_outbox"
LOG = TMP / "paxect_demo1_log.jsonl"
POLICY = TMP / "paxect_demo1_policy.json"

# Ensure dirs
for d in (INBOX, OUTBOX): d.mkdir(parents=True, exist_ok=True)

# Make policy friendlier for first run (trust hostname + localhost)
hn = socket.gethostname()
POLICY.write_text("""{
  "version": "1.2.0",
  "trusted_nodes": ["%s","localhost"],
  "allowed_suffixes": [".bin",".txt",".json",".csv",".aead",".freq"],
  "max_file_mb": 256,
  "require_sig": false,
  "auto_delete": true,
  "log_level": "info"
}""" % hn)

# Env for Link Plugin
os.environ.update({
    "PAXECT_LINK_INBOX": str(INBOX),
    "PAXECT_LINK_OUTBOX": str(OUTBOX),
    "PAXECT_LINK_LOG": str(LOG),
    "PAXECT_LINK_POLICY": str(POLICY),
    "PAXECT_CORE": f"python {CORE}",
})

# Seed an input file
(INBOX / "example.txt").write_text("PAXECT Demo 1 — local relay\n", encoding="utf-8")

# Run Link briefly, then stop
p = subprocess.Popen(["python", str(LINK)])
time.sleep(8)

# Verify
dec = list(OUTBOX.glob("*"))
print("decoded:", [x.name for x in dec])

# Shutdown
p.send_signal(signal.SIGINT)
try: p.wait(timeout=5)
except subprocess.TimeoutExpired: p.kill()

print("✅ Demo 1 complete")
