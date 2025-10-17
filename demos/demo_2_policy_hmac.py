#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link — Demo 2: Policy + HMAC Enforcement (enterprise)
Purpose: require signed peer manifests; accept signed peer, reject unsigned.
"""

import os, time, json, hmac, hashlib, tempfile, subprocess, signal, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = ROOT / "paxect_link_plugin.py"
CORE = ROOT / "paxect_core.py"

TMP = Path(tempfile.gettempdir()) / "paxect_demo2"
INBOX = TMP / "inbox"
OUTBOX = TMP / "outbox"
LOG = TMP / "log.jsonl"
POLICY = TMP / "policy.json"
MANIFEST_GOOD = TMP / "link_manifest_node2.json"
MANIFEST_BAD  = TMP / "link_manifest_evil.json"

HKEY = "supersecret-demo-hmac-key"
HN = socket.gethostname()

# Dirs
for p in (TMP, INBOX, OUTBOX): p.mkdir(parents=True, exist_ok=True)
if LOG.exists(): LOG.unlink()

# Strict policy: require_sig=true; trust node2 + localhost + current host
POLICY.write_text(json.dumps({
    "version": "1.2.0",
    "trusted_nodes": [HN, "localhost", "node2"],
    "allowed_suffixes": [".bin",".txt",".json",".csv",".aead",".freq"],
    "max_file_mb": 256,
    "require_sig": True,
    "auto_delete": True,
    "log_level": "info"
}, indent=2))

# Helper: HMAC sign
def sign_payload(payload: dict, key: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()

# Good peer manifest (node2)
payload = {
    "datetime_utc": "2099-01-01 00:00:00 UTC",
    "node": "node2",
    "platform": "Linux",
    "policy": POLICY.name,
    "inbox": str(INBOX.resolve()),
    "outbox": str(OUTBOX.resolve()),
    "version": "1.2.0"
}
MANIFEST_GOOD.write_text(json.dumps({"payload": payload, "hmac_sha256": sign_payload(payload, HKEY)}, indent=2), encoding="utf-8")

# Bad (unsigned) manifest
MANIFEST_BAD.write_text(json.dumps({"payload": {"node":"evil"}, "hmac_sha256": ""}, indent=2), encoding="utf-8")

# Env for Link Plugin (run from TMP so manifests are discovered)
env = os.environ.copy()
env.update({
    "PAXECT_LINK_INBOX": str(INBOX),
    "PAXECT_LINK_OUTBOX": str(OUTBOX),
    "PAXECT_LINK_LOG": str(LOG),
    "PAXECT_LINK_POLICY": str(POLICY),
    "PAXECT_LINK_HMAC_KEY": HKEY,
    "PAXECT_CORE": f"python {CORE}",
})

# Seed
(INBOX / "contract.txt").write_text("Demo 2 — policy + HMAC\n", encoding="utf-8")

# Run Link
p = subprocess.Popen(["python", str(LINK)], cwd=str(TMP), env=env)
time.sleep(10)

print("decoded:", [x.name for x in OUTBOX.glob("*")])

# Stop
p.send_signal(signal.SIGINT)
try: p.wait(timeout=5)
except subprocess.TimeoutExpired: p.kill()

# Show handshake evidence
if LOG.exists():
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if '"handshake"' in line or 'handshake_reject' in line:
            print(line)

print("✅ Demo 2 complete")
