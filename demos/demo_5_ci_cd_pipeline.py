#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
PAXECT — Demo 5: CI/CD Pipeline Smoke (JUnit XML)
Purpose: smoke tests for core and link; emits JUnit XML for CI systems.
"""

import os, sys, time, json, tempfile, subprocess, hashlib, socket
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "paxect_core.py"
LINK = ROOT / "paxect_link_plugin.py"

TMP = Path(tempfile.gettempdir()) / "paxect_demo5"
INBOX = TMP / "inbox"; OUTBOX = TMP / "outbox"; LOG = TMP / "log.jsonl"; POLICY = TMP / "policy.json"
ART = TMP / "junit_smoke.xml"
for d in (INBOX, OUTBOX): d.mkdir(parents=True, exist_ok=True)

def run(cmd, **kw):
    r=subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r.returncode, r.stdout, r.stderr

tests=[]

# Test 1: core encode/decode roundtrip
data = TMP / "data.txt"
data.write_text("PAXECT CI roundtrip\n", encoding="utf-8")
freq = TMP / "data.freq"
out  = TMP / "data.out"

rc, so, se = run(["python", str(CORE), "encode", "-i", str(data), "-o", str(freq)])
tests.append(("core_encode", rc==0, so+se))
rc, so, se = run(["python", str(CORE), "decode", "-i", str(freq), "-o", str(out), "--verify"])
ok = (rc==0 and out.read_text(encoding="utf-8")==data.read_text(encoding="utf-8"))
tests.append(("core_decode_verify", ok, so+se))

# Test 2: link relay smoke
hn = socket.gethostname()
POLICY.write_text(json.dumps({
  "version":"1.2.0",
  "trusted_nodes":["localhost", hn],
  "allowed_suffixes":[".txt",".freq",".json"],
  "max_file_mb":8,
  "require_sig":False,
  "auto_delete":True,
  "log_level":"info"
}, indent=2), encoding="utf-8")

env=os.environ.copy()
env["PAXECT_LINK_INBOX"]=str(INBOX)
env["PAXECT_LINK_OUTBOX"]=str(OUTBOX)
env["PAXECT_LINK_LOG"]=str(LOG)
env["PAXECT_LINK_POLICY"]=str(POLICY)
env["PAXECT_CORE"]=f"python {CORE}"

(INBOX/"ci.txt").write_text("CI via link relay\n", encoding="utf-8")
p=subprocess.Popen(["python", str(LINK)], env=env, cwd=str(TMP))
time.sleep(8)
dec=list(OUTBOX.glob("*"))
tests.append(("link_relay_decoded", len(dec)>=1, f"decoded={ [d.name for d in dec] }"))
p.send_signal(subprocess.signal.SIGINT)
try: p.wait(timeout=5)
except subprocess.TimeoutExpired: p.kill()

# Emit JUnit XML
passed=sum(1 for _,ok,_ in tests if ok)
failed=len(tests)-passed
xml=['<?xml version="1.0" encoding="UTF-8"?>',
     f'<testsuite name="paxect_smoke" tests="{len(tests)}" failures="{failed}">']
for name, ok, txt in tests:
    if ok:
        xml.append(f'  <testcase name="{escape(name)}"/>')
    else:
        xml.append(f'  <testcase name="{escape(name)}">')
        xml.append(f'    <failure message="failed">{escape(txt or "")}</failure>')
        xml.append('  </testcase>')
xml.append('</testsuite>')
TMP.mkdir(parents=True, exist_ok=True)
ART.write_text("\n".join(xml), encoding="utf-8")

print(f"\n=== CI Smoke Summary ===")
for name, ok, txt in tests:
    print(f"{'PASS' if ok else 'FAIL'} - {name}")
print(f"\nJUnit XML: {ART}")

sys.exit(0 if failed==0 else 1)
