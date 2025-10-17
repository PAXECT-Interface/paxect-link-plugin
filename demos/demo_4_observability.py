#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT Link — Demo 4: Observability from JSONL (enterprise)
Purpose: parse the JSONL logs to show counts, levels, and recent lines.
"""

import os, json, time, tempfile, subprocess, signal, collections, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = ROOT / "paxect_link_plugin.py"
CORE = ROOT / "paxect_core.py"

TMP = Path(tempfile.gettempdir()) / "paxect_demo4"
INBOX = TMP / "inbox"
OUTBOX = TMP / "outbox"
LOG = TMP / "log.jsonl"
POLICY = TMP / "policy.json"

for d in (INBOX, OUTBOX): d.mkdir(parents=True, exist_ok=True)
if LOG.exists(): LOG.unlink()

hn = socket.gethostname()
POLICY.write_text(json.dumps({
  "version":"1.2.0",
  "trusted_nodes":[hn,"localhost"],
  "allowed_suffixes":[".txt",".json",".freq",".csv"],
  "max_file_mb":2,
  "require_sig":False,
  "auto_delete":True,
  "log_level":"debug"
}, indent=2), encoding="utf-8")

# Inputs (one will be blocked by suffix policy)
(INBOX/"ok1.txt").write_text("alpha\n", encoding="utf-8")
(INBOX/"ok2.csv").write_text("x,y\n1,2\n", encoding="utf-8")
(INBOX/"blocked.exe").write_text("nope\n", encoding="utf-8")

# Run Link
p=subprocess.Popen(["python", str(LINK)],
                   env={"PAXECT_LINK_INBOX":str(INBOX),
                        "PAXECT_LINK_OUTBOX":str(OUTBOX),
                        "PAXECT_LINK_LOG":str(LOG),
                        "PAXECT_LINK_POLICY":str(POLICY),
                        "PAXECT_CORE":f"python {CORE}"},
                   cwd=str(TMP))
time.sleep(10)

# Stop
p.send_signal(signal.SIGINT)
try: p.wait(timeout=5)
except subprocess.TimeoutExpired: p.kill()

# Parse log
events=collections.Counter()
levels=collections.Counter()
decoded=0
blocks=0
recent=[]
if LOG.exists():
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            j=json.loads(line)
            events[j.get("event","?")]+=1
            levels[j.get("level","info")]+=1
            if j.get("event")=="decode": decoded+=1
            if j.get("event")=="policy_block": blocks+=1
            recent=([line]+recent)[:5]
        except: pass

print("\n=== Observability Summary ===")
print(f"Events: {dict(events)}")
print(f"Levels: {dict(levels)}")
print(f"Decoded files: {decoded}")
print(f"Policy blocks: {blocks}")
print("\nRecent log lines:")
for l in recent: print(l)
print("\nOutbox contents:", [p.name for p in OUTBOX.glob('*')])
print("\n✅ Demo 4 complete")
