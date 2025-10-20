#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Demo 5 — CI/CD Pipeline Smoke Test (Enterprise Hardened)
--------------------------------------------------------
Purpose
--------
Runs a deterministic smoke suite for automated verification of:
1. PAXECT Core encode/decode integrity
2. PAXECT Link Plugin relay operation
3. Generates a JUnit XML report for CI systems

Features
--------
- Automatic cleanup of old lock files
- Deterministic runtime (no randomness, no telemetry)
- Zero dependencies outside Python stdlib
- Self-cleaning temporary workspace
"""

import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

# === Base directory for temporary state ===
BASE = Path("/tmp/paxect_demo5")
BASE.mkdir(parents=True, exist_ok=True)

XML_PATH = BASE / "junit_smoke.xml"
INPUT = BASE / "demo_input.txt"
ENCODED = BASE / "demo_input.freq"
DECODED = BASE / "demo_output.txt"
LOCK = BASE / ".paxect_link.lock"

# Clean any stale lock before start
try:
    LOCK.unlink()
except FileNotFoundError:
    pass

INPUT.write_text("paxect smoke test\n", encoding="utf-8")
results = []


def record(testname: str, ok: bool, msg: str = ""):
    """Record a test result and print concise summary."""
    status = "PASS" if ok else "FAIL"
    print(f"{status} - {testname}")
    results.append((testname, ok, msg))


# === 1. Core encode/decode ===
def test_core_roundtrip():
    """Validate PAXECT Core encode/decode determinism."""
    try:
        subprocess.run(
            ["python3", "paxect_core.py", "encode", "-i", str(INPUT), "-o", str(ENCODED)],
            check=True,
            timeout=6,
        )
        subprocess.run(
            ["python3", "paxect_core.py", "decode", "-i", str(ENCODED), "-o", str(DECODED)],
            check=True,
            timeout=6,
        )
        ok = DECODED.exists() and "paxect smoke" in DECODED.read_text()
        record("core_encode_decode", ok)
    except Exception as e:
        record("core_encode_decode", False, str(e))


# === 2. Link relay ===
def test_link_relay():
    """Validate that the Link plugin can relay a file end-to-end."""
    inbox = BASE / "inbox"
    outbox = BASE / "outbox"
    policy = BASE / "policy.json"

    # Clean environment
    shutil.rmtree(inbox, ignore_errors=True)
    shutil.rmtree(outbox, ignore_errors=True)
    inbox.mkdir(parents=True)
    outbox.mkdir(parents=True)

    # Remove any leftover lock before run
    try:
        LOCK.unlink()
    except FileNotFoundError:
        pass

    # Write a minimal policy
    policy.write_text(
        """{
          "trusted_nodes": ["localhost", "PAXECT-Interface"],
          "allowed_suffixes": [".txt", ".freq"],
          "auto_delete": true,
          "log_level": "info"
        }""",
        encoding="utf-8",
    )

    # Place a relay input
    (inbox / "relay.txt").write_text("relay via link plugin\n", encoding="utf-8")

    env = os.environ.copy()
    env.update({
        "PAXECT_LINK_INBOX": str(inbox),
        "PAXECT_LINK_OUTBOX": str(outbox),
        "PAXECT_LINK_POLICY": str(policy),
        "PAXECT_LINK_LOCK": str(LOCK),
        "PAXECT_CORE": "python3 paxect_core.py",
        "PAXECT_LINK_POLL_SEC": "1.0",
    })

    try:
        subprocess.run(
            ["python3", "paxect_link_plugin.py"],
            env=env,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        # Safe and expected: Link plugin polls until timeout
        pass

    ok = any(outbox.glob("relay"))
    record("link_relay_decoded", ok)


# === 3. JUnit XML report ===
def write_junit_xml():
    """Write results to JUnit XML for CI integration."""
    suite = ET.Element("testsuite", name="PAXECT-Smoke", tests=str(len(results)))
    for name, ok, msg in results:
        tc = ET.SubElement(suite, "testcase", name=name)
        if not ok:
            fail = ET.SubElement(tc, "failure", message=msg)
            fail.text = msg
    tree = ET.ElementTree(suite)
    tree.write(XML_PATH, encoding="utf-8", xml_declaration=True)
    print(f"JUnit report written to: {XML_PATH}")


# === Main entry ===
def main():
    print("=== Demo 5 — CI/CD Smoke Suite (Enterprise Hardened) ===")
    test_core_roundtrip()
    test_link_relay()
    write_junit_xml()

    all_ok = all(ok for _, ok, _ in results)
    exit_code = 0 if all_ok else 1
    print(f"exit={exit_code}")
    print("✅ Demo 5 complete" if all_ok else "⚠️ Demo 5 failed")

    # Full cleanup
    shutil.rmtree(BASE, ignore_errors=True)
    exit(exit_code)


if __name__ == "__main__":
    main()
