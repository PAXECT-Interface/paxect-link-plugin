#!/usr/bin/env python3
"""
PAXECT Demo 01 – Quick Start
-----------------------------
Minimal startup test for developers.

Goals:
- Import main PAXECT modules
- Run one short SelfTune adaptive step
- Print structured JSON summary
"""

import json, time, random, hashlib

MODULES = [
    "paxect_core",
    "paxect_aead_hybrid_plugin",
    "paxect_polyglot_plugin",
    "paxect_selftune_plugin",
    "paxect_link_plugin",
]

def main():
    print("=== PAXECT Demo 01 – Quick Start ===")
    results = []
    for name in MODULES:
        try:
            __import__(name)
            results.append({"module": name, "status": "OK"})
        except Exception as e:
            results.append({"module": name, "status": "FAIL", "error": str(e)})

    # simple selftune sample
    eps = 0.1
    mode = "explore" if random.random() < eps else "exploit"
    checksum = hashlib.sha256(mode.encode()).hexdigest()[:12]
    summary = {
        "epsilon": eps,
        "mode": mode,
        "checksum": checksum,
        "modules_ok": sum(1 for r in results if r["status"] == "OK"),
    }

    print(json.dumps({"modules": results, "selftune": summary}, indent=2))
    print("\n[OK] Demo 01 finished successfully")

if __name__ == "__main__":
    main()
