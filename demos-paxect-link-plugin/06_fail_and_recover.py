#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Demo 6 — Fail & Self-Recover (Resilient Relay)

- Drops 1 valid .txt and 1 corrupted .freq (+ bad sidecar)
- Verifies: checksum_mismatch logged AND valid file still relayed
"""

import os
import json
import time
import subprocess
from pathlib import Path
import shutil
import signal

BASE = Path("/tmp/paxect_demo6")
INBOX = BASE / "inbox"
OUTBOX = BASE / "outbox"
POLICY = BASE / "policy.json"
LOCK = BASE / ".paxect_link.lock"
LOG = BASE / "link_log.jsonl"

LINK = Path("paxect_link_plugin.py")  # repo entrypoint
CORE = os.environ.get("PAXECT_CORE", "python3 paxect_core_plugin.py")  # allow override

# === Clean environment ===
shutil.rmtree(BASE, ignore_errors=True)
INBOX.mkdir(parents=True)
OUTBOX.mkdir(parents=True)

# === Write policy ===
POLICY.write_text(json.dumps({
    "trusted_nodes": ["localhost", "PAXECT-Interface"],
    "allowed_suffixes": [".txt", ".freq"],
    "auto_delete": True,
    "log_level": "info",
    "quarantine_on_policy_block": True
}, indent=2))

# === Create test files ===
(INBOX / "ok.txt").write_text("this file is fine\n", encoding="utf-8")

bad_freq = INBOX / "bad.freq"
bad_freq.write_bytes(b"\x00\x11\x22corrupteddata")#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Demo 6 — Fail & Self-Recover (Resilient Relay)
----------------------------------------------
Purpose
--------
Showcase automatic failure handling and recovery within the
PAXECT Link Plugin. Demonstrates that the plugin can detect a
corrupted input (.freq with bad checksum), log the failure,
and continue normally with valid files.
"""

import os
import json
import time
import subprocess
from pathlib import Path
import shutil

BASE = Path("/tmp/paxect_demo6")
INBOX = BASE / "inbox"
OUTBOX = BASE / "outbox"
POLICY = BASE / "policy.json"
LOCK = BASE / ".paxect_link.lock"
LOG = BASE / "link_log.jsonl"

# === Clean environment ===
shutil.rmtree(BASE, ignore_errors=True)
INBOX.mkdir(parents=True)
OUTBOX.mkdir(parents=True)

# === Write policy ===
POLICY.write_text(json.dumps({
    "trusted_nodes": ["localhost", "PAXECT-Interface"],
    "allowed_suffixes": [".txt", ".freq"],
    "auto_delete": True,
    "log_level": "info"
}, indent=2))

# === Create test files ===
# Valid file
(INBOX / "ok.txt").write_text("this file is fine\n", encoding="utf-8")

# Corrupted file (bad checksum sidecar)
bad_freq = INBOX / "bad.freq"
bad_freq.write_bytes(b"\x00\x11\x22corrupteddata")
(bad_freq.with_suffix(".freq.sha256")).write_text("deadbeef", encoding="ascii")

# === Environment ===
env = os.environ.copy()
env.update({
    "PAXECT_LINK_INBOX": str(INBOX),
    "PAXECT_LINK_OUTBOX": str(OUTBOX),
    "PAXECT_LINK_POLICY": str(POLICY),
    "PAXECT_LINK_LOCK": str(LOCK),
    "PAXECT_LINK_LOG": str(LOG),
    "PAXECT_CORE": "python3 paxect_core.py",
    "PAXECT_LINK_POLL_SEC": "1.0",
    "PAXECT_LINK_BACKOFF_SEC": "2.0"
})

# === Run Link Plugin ===
print("=== Demo 6 — Fail & Self-Recover ===")
print("Injecting 1 valid and 1 corrupted file...")

try:
    subprocess.run(["python3", "paxect_link_plugin.py"], env=env, timeout=10)
except subprocess.TimeoutExpired:
    print("[ℹ] Timeout reached (normal behavior).")

# === Inspect log ===
print("\n[+] Checking log for failure & recovery events:")
if LOG.exists():
    lines = LOG.read_text(encoding="utf-8").splitlines()
    recent = [ln for ln in lines[-10:]]
    for ln in recent:
        print("  ", ln)
else:
    print("  (no log found)")

# === Check output ===
decoded = [p.name for p in OUTBOX.glob("*") if p.is_file()]
print(f"\n[+] Outbox files: {decoded or '— none —'}")

if decoded:
    print("✅ Self-recovery confirmed — system continued after failure.")
else:
    print("⚠️ Recovery not confirmed — check log for decode_error events.")
(bad_freq.with_suffix(".freq.sha256")).write_text("deadbeef", encoding="ascii")

# === Environment ===
env = os.environ.copy()
env.update({
    "PAXECT_LINK_INBOX": str(INBOX),
    "PAXECT_LINK_OUTBOX": str(OUTBOX),
    "PAXECT_LINK_POLICY": str(POLICY),
    "PAXECT_LINK_LOCK": str(LOCK),
    "PAXECT_LINK_LOG": str(LOG),
    "PAXECT_CORE": CORE,
    "PAXECT_LINK_POLL_SEC": "0.5",
    "PAXECT_LINK_BACKOFF_SEC": "1.0",
    "PAXECT_LINK_PREFLIGHT": "0",   # keep demo fast; core down shouldn’t block checksum test
})

print("=== Demo 6 — Fail & Self-Recover ===")
print("Injecting 1 valid and 1 corrupted file...")

# === Run Link Plugin as background watcher ===
proc = subprocess.Popen(["python3", str(LINK)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    time.sleep(6)  # allow a few polls
finally:
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()

# === Inspect log ===
print("\n[+] Checking log for failure & recovery events:")
events = []
if LOG.exists():
    for ln in LOG.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(ln).get("event"))
        except Exception:
            pass
else:
    print("  (no log found)")

print("  events:", {e: events.count(e) for e in set(events)} if events else "— none —")

# === Check output ===
decoded = sorted([p.name for p in OUTBOX.glob("*") if p.is_file()])
print(f"\n[+] Outbox files: {decoded or '— none —'}")

ok = ("ok" in decoded)
bad_logged = ("checksum_mismatch" in events)

if ok and bad_logged:
    print("✅ Self-recovery confirmed — checksum failure logged AND valid file relayed.")
else:
    print("⚠️ Not confirmed.")
    if not ok:
        print("  - Missing outbox/ok (valid relay failed)")
    if not bad_logged:
        print("  - Missing checksum_mismatch event in log")
