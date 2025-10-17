#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link — Demo 3: Multi-Node Relay (enterprise)
Purpose: run two Link instances (nodeA & nodeB), both signed; verify decode on both.
"""

import os, time, json, hmac, hashlib, tempfile, subprocess, signal, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = ROOT / "paxect_link_plugin.py"
CORE = ROOT / "paxect_core.py"
HKEY = "supersecret-demo-hmac-key"
HN = socket.gethostname()

BASE = Path(tempfile.gettempdir()) / "paxect_demo3"
WORK = BASE / "work"
A = BASE / "nodeA"
B = BASE / "nodeB"
for p in (WORK, A, B):
    (p/"inbox").mkdir(parents=True, exist_ok=True)
    (p/"outbox").mkdir(parents=True, exist_ok=True)

# Policy that trusts nodeA, nodeB, localhost, and the current host
POLICY = {
  "version":"1.2.0",
  "trusted_nodes":["nodeA","nodeB","localhost", HN],
  "allowed_suffixes":[".bin",".txt",".json",".csv",".aead",".freq"],
  "max_file_mb":256,
  "require_sig":True,
  "auto_delete":True,
  "log_level":"info"
}

def sign(payload: dict)->str:
    body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(HKEY.encode(), body, hashlib.sha256).hexdigest()

def env_for(node_dir: Path, node_name: str):
    e=os.environ.copy()
    e["PAXECT_LINK_INBOX"]=str(node_dir/"inbox")
    e["PAXECT_LINK_OUTBOX"]=str(node_dir/"outbox")
    e["PAXECT_LINK_LOG"]=str(node_dir/"log.jsonl")
    e["PAXECT_LINK_POLICY"]=str(node_dir/"policy.json")
    e["PAXECT_LINK_MANIFEST"]=str(WORK/f"link_manifest_{node_name}.json")
    # Per-node lock so both instances can run concurrently
    e["PAXECT_LINK_LOCK"]=str(node_dir/".paxect_link.lock")
    e["PAXECT_LINK_HMAC_KEY"]=HKEY
    e["PAXECT_CORE"]=f"python {CORE}"
    (node_dir/"policy.json").write_text(json.dumps(POLICY, indent=2), encoding="utf-8")
    return e

def seed_peer_manifests():
    for node_name in ("nodeA","nodeB"):
        payload={
          "datetime_utc":"2099-01-01 00:00:00 UTC",
          "node":node_name,
          "platform":"Linux",
          "policy":"policy.json",
          "inbox":str((BASE/node_name/"inbox").resolve()),
          "outbox":str((BASE/node_name/"outbox").resolve()),
          "version":"1.2.0"
        }
        (WORK/f"link_manifest_{node_name}.json").write_text(
            json.dumps({"payload":payload,"hmac_sha256":sign(payload)}, indent=2), encoding="utf-8"
        )

envA=env_for(A,"nodeA")
envB=env_for(B,"nodeB")
seed_peer_manifests()

# Seed inputs
(A/"inbox"/"A.txt").write_text("Hello from A\n", encoding="utf-8")
(B/"inbox"/"B.txt").write_text("Hello from B\n", encoding="utf-8")

print("[*] starting nodeA and nodeB…")
pA=subprocess.Popen(["python", str(LINK)], cwd=str(WORK), env=envA)
pB=subprocess.Popen(["python", str(LINK)], cwd=str(WORK), env=envB)

time.sleep(12)

decA=[p.name for p in (A/"outbox").glob("*")]
decB=[p.name for p in (B/"outbox").glob("*")]
print(f"[+] nodeA decoded: {decA}")
print(f"[+] nodeB decoded: {decB}")

print("[*] stopping both…")
for p in (pA,pB):
    p.send_signal(signal.SIGINT)
    try: p.wait(timeout=5)
    except subprocess.TimeoutExpired: p.kill()

# Show handshake lines
for node_dir, tag in ((A,"A"), (B,"B")):
    log=node_dir/"log.jsonl"
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            if '"handshake"' in line:
                print(f"[node{tag}] {line}")

print("✅ Demo 3 complete")
