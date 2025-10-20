#!/usr/bin/env python3
"""
PAXECT Demo 09 – Enterprise All-in-One
--------------------------------------
Runs every validated demo (01-08) sequentially, probes observability
endpoints, aggregates all results into one JSON report.

This represents a full-system, multi-plugin verification pass.
"""

import subprocess, json, time, urllib.request, tempfile, sys, os
from pathlib import Path

DEMOS = [
    "demo_01_quick_start.py",
    "demo_02_integration_loop.py",
    "demo_03_safety_throttle.py",
    "demo_04_metrics_health.py",
    "demo_05_link_smoke.sh",
    "demo_06_polyglot_bridge.py",
    "demo_07_selftune_adaptive.py",
    "demo_08_secure_multichannel_aead_hybrid.py",
]

REPORT = Path(tempfile.gettempdir()) / "paxect_demo_09_all_in_one.json"

def run_demo(path):
    """Run a demo and capture its outcome."""
    start = time.time()
    if not Path(path).exists():
        return {"demo": path, "status": "MISSING"}
    cmd = ["bash", path] if path.endswith(".sh") else [sys.executable, path]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        ok = proc.returncode == 0 and "error" not in proc.stderr.lower()
        status = "OK" if ok else "FAIL"
    except subprocess.TimeoutExpired:
        status = "TIMEOUT"
    return {
        "demo": path,
        "status": status,
        "elapsed_s": round(time.time() - start, 2),
    }

def check_endpoint(endpoint):
    """Ping observability endpoints."""
    url = f"http://127.0.0.1:8081/{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return {"endpoint": endpoint, "status": r.status, "ok": True}
    except Exception as e:
        return {"endpoint": endpoint, "status": str(e), "ok": False}

def main():
    print("=== PAXECT Demo 09 – Enterprise All-in-One ===")
    results = []
    for demo in DEMOS:
        print(f"[RUN] {demo} ...")
        results.append(run_demo(demo))
    print("[CHECK] Observability endpoints ...")
    obs = [check_endpoint(x) for x in ("ping", "ready", "metrics", "last")]
    summary = {
        "timestamp": int(time.time()),
        "results": results,
        "observability": obs,
    }
    REPORT.write_text(json.dumps(summary, indent=2))
    ok_count = sum(1 for r in results if r["status"] == "OK")
    print(f"[OK] {ok_count}/{len(DEMOS)} demos succeeded")
    print(f"[SAVED] Report written to {REPORT}")
    print("[DONE] Enterprise validation complete ✅")

if __name__ == "__main__":
    main()
