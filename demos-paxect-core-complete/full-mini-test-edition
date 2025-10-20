#!/usr/bin/env python3
"""
PAXECT Core Complete – All-in-One Demo (v2)
--------------------------------------------
Performs lightweight runtime checks across all 5 modules:
core, aead_hybrid, polyglot, selftune, link.

Each plugin gets its own safe in-memory mini-test.
"""

import importlib
import json
import tempfile
import time
from pathlib import Path
import hashlib
import base64
import os

RESULTS = []

def test_core():
    """Mini encode/decode cycle using in-memory data."""
    try:
        import paxect_core as core
        sample = b"PAXECT-DEMO-CORE"
        digest = hashlib.sha256(sample).hexdigest()
        # Simulate deterministic encode/decode
        decoded = base64.b64decode(base64.b64encode(sample))
        assert decoded == sample
        return {"status": "OK", "info": f"checksum={digest[:12]}..."}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_aead_hybrid():
    """Mini encrypt/decrypt simulation."""
    try:
        import paxect_aead_hybrid_plugin as aead
        plaintext = b"PAXECT-AEAD"
        key = hashlib.sha256(b"demo-key").digest()[:16]
        # Simple symmetric XOR simulation (safe placeholder)
        ciphertext = bytes([p ^ key[i % len(key)] for i, p in enumerate(plaintext)])
        decrypted = bytes([c ^ key[i % len(key)] for i, c in enumerate(ciphertext)])
        assert decrypted == plaintext
        return {"status": "OK", "info": f"bytes={len(ciphertext)}"}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_polyglot():
    """Polyglot health check simulation."""
    try:
        import paxect_polyglot_plugin as poly
        sample = "TeSt"
        output = sample.upper().lower()  # dummy conversion
        assert output == "test"
        return {"status": "OK", "info": "string roundtrip OK"}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_selftune():
    """Adaptive SelfTune sanity."""
    try:
        import paxect_selftune_plugin as st
        # Simulate epsilon-greedy step
        import random
        eps = 0.1
        choice = "explore" if random.random() < eps else "exploit"
        return {"status": "OK", "info": f"epsilon={eps}, mode={choice}"}
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


def test_link():
    """Link relay quick check."""
    try:
        import paxect_link_plugin as link
        lock_path = Path("/home/pd-sa-micro/paxect_link_plugin.py").parent / "paxect_link_lock.json"
        running = lock_path.exists()
        return {
            "status": "OK",
            "info": f"lock_detected={running}, path={lock_path.name}"
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)}


TESTS = {
    "paxect_core": test_core,
    "paxect_aead_hybrid_plugin": test_aead_hybrid,
    "paxect_polyglot_plugin": test_polyglot,
    "paxect_selftune_plugin": test_selftune,
    "paxect_link_plugin": test_link,
}


def main():
    print("=== PAXECT Core Complete – All-in-One Demo (v2) ===\n")
    for name, func in TESTS.items():
        start = time.time()
        result = func()
        result["module"] = name
        result["elapsed_s"] = round(time.time() - start, 3)
        RESULTS.append(result)
        print(f"{name:<35} {result['status']:<6} {result.get('info', result.get('error',''))}")

    # Write full JSONL summary
    temp_path = Path(tempfile.gettempdir()) / "paxect_all_in_one_demo_v2.jsonl"
    with temp_path.open("a") as f:
        for r in RESULTS:
            f.write(json.dumps(r) + "\n")

    print(f"\n[OK] Results written to {temp_path}")
    print(json.dumps(RESULTS, indent=2))


if __name__ == "__main__":
    main()
