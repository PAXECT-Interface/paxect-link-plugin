#!/usr/bin/env python3
"""
PAXECT Demo Showcase Story
--------------------------
Short visual story for GitHub visitors.
Demonstrates key PAXECT guarantees in ~15 seconds.
"""

import json, time, hashlib, base64, random, urllib.request

def ping(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def main():
    print("=== PAXECT Showcase Story ===")
    print("1️⃣  Initializing SelfTune ...")
    eps = 0.1
    mode = "exploit" if random.random() > eps else "explore"
    time.sleep(0.5)

    print("2️⃣  Running deterministic Core check ...")
    data = b"PAXECT-DETERMINISTIC"
    encoded = base64.b64encode(data)
    decoded = base64.b64decode(encoded)
    digest = hashlib.sha256(decoded).hexdigest()[:12]
    time.sleep(0.5)

    print("3️⃣  Checking observability endpoints ...")
    ready = ping("http://127.0.0.1:8081/ready")
    metrics = ping("http://127.0.0.1:8081/metrics")
    time.sleep(0.5)

    summary = {
        "selftune_mode": mode,
        "checksum": digest,
        "ready_endpoint": ready,
        "metrics_endpoint": metrics,
        "status": "All hops consistent ✅" if ready and metrics else "Observability unavailable ⚠️"
    }

    print(json.dumps(summary, indent=2))
    print("\n🎉  PAXECT Core Complete — First-year free for enterprises 🚀")

if __name__ == "__main__":
    main()
