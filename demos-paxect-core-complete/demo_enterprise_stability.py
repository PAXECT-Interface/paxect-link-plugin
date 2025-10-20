#!/usr/bin/env python3
"""
PAXECT Demo Enterprise B – Stability Loop
-----------------------------------------
Long-running durability & stability simulator.

Features:
 - Configurable run duration (DEV friendly via env var)
 - Periodic mini-tests (calls to the same safe test functions used earlier)
 - JSONL append logs for each run iteration (persisted to /tmp)
 - Simple restart-on-exception loop (keeps running)
 - Writes heartbeat + summary every iteration
 - Signal-friendly (KeyboardInterrupt exits cleanly)

Env vars (examples):
  RUN_SECONDS       total runtime in seconds (default 86400 = 24h)
  ITERATION_S       seconds between iterations (default 30)
  LOG_PATH          path for JSONL logs (default /tmp/paxect_enterprise_stability.jsonl)
  SAFE_MODE         "1" => shorter iterations & dev-friendly behaviour

Run (dev quick test):
  SAFE_MODE=1 RUN_SECONDS=60 ITERATION_S=5 python3 demo_enterprise_stability.py

Run (prod 24h):
  python3 demo_enterprise_stability.py

"""

import os, time, json, traceback, random, signal
from pathlib import Path
from datetime import datetime, timezone

# Config
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "86400"))  # default 24h
ITERATION_S = int(os.environ.get("ITERATION_S", "30"))
LOG_PATH = Path(os.environ.get("LOG_PATH", "/tmp/paxect_enterprise_stability.jsonl"))
SAFE_MODE = os.environ.get("SAFE_MODE", "0") == "1"

if SAFE_MODE:
    # Override for quick dev cycles
    RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "60"))
    ITERATION_S = int(os.environ.get("ITERATION_S", "5"))

_stop = False
def _sigterm(signum, frame):
    global _stop
    _stop = True
signal.signal(signal.SIGINT, _sigterm)
signal.signal(signal.SIGTERM, _sigterm)

# Reuse small safe test functions (lightweight)
def _test_core():
    try:
        import paxect_core as core
        return {"module":"paxect_core","status":"OK"}
    except SystemExit as e:
        return {"module":"paxect_core","status":"CLI EXIT","error":str(e)}
    except Exception as e:
        return {"module":"paxect_core","status":"FAIL","error":str(e)}

def _test_aead():
    try:
        import paxect_aead_hybrid_plugin as a
        return {"module":"paxect_aead_hybrid_plugin","status":"OK"}
    except SystemExit as e:
        return {"module":"paxect_aead_hybrid_plugin","status":"CLI EXIT","error":str(e)}
    except Exception as e:
        return {"module":"paxect_aead_hybrid_plugin","status":"FAIL","error":str(e)}

def _test_polyglot():
    try:
        import paxect_polyglot_plugin as p
        return {"module":"paxect_polyglot_plugin","status":"OK"}
    except SystemExit as e:
        return {"module":"paxect_polyglot_plugin","status":"CLI EXIT","error":str(e)}
    except Exception as e:
        return {"module":"paxect_polyglot_plugin","status":"FAIL","error":str(e)}

def _test_selftune():
    try:
        import paxect_selftune_plugin as s
        # lightweight simulated metric
        eps = 0.1
        mode = "explore" if random.random() < eps else "exploit"
        return {"module":"paxect_selftune_plugin","status":"OK","mode":mode}
    except Exception as e:
        return {"module":"paxect_selftune_plugin","status":"FAIL","error":str(e)}

def _test_link():
    try:
        import paxect_link_plugin as l
        # check lock heuristic
        lock_path = Path("/home/pd-sa-micro/paxect_link_lock.json")
        return {"module":"paxect_link_plugin","status":"OK","lock":lock_path.exists()}
    except Exception as e:
        return {"module":"paxect_link_plugin","status":"FAIL","error":str(e)}

TEST_FUNCS = [_test_core, _test_aead, _test_polyglot, _test_selftune, _test_link]

def _now_ts():
    return int(time.time())

def _iso_now():
    return datetime.now(timezone.utc).isoformat()

def append_log(entry: dict):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

def run_loop():
    start_ts = _now_ts()
    deadline = start_ts + RUN_SECONDS
    iteration = 0
    print(f"[stability] Starting loop for {RUN_SECONDS}s (iter every {ITERATION_S}s). Log: {LOG_PATH}")
    while not _stop and _now_ts() < deadline:
        iteration += 1
        iter_start = time.time()
        entry = {
            "ts": _now_ts(),
            "iso": _iso_now(),
            "iteration": iteration,
            "status": "running",
            "results": [],
        }
        try:
            # run each mini-test (safe)
            for fn in TEST_FUNCS:
                r = fn()
                entry["results"].append(r)
            # compute summary
            ok = sum(1 for r in entry["results"] if r.get("status") == "OK")
            entry["summary"] = {"total": len(entry["results"]), "ok": ok}
            entry["status"] = "ok" if ok == len(entry["results"]) else "degraded"
            entry["duration_s"] = round(time.time() - iter_start, 3)
            append_log(entry)
            # print compact status to stdout for live monitoring
            print(f"[{iteration:04d}] {entry['iso']}  status={entry['status']} ok={ok}/{len(entry['results'])} dur={entry['duration_s']}s")
        except Exception as exc:
            tb = traceback.format_exc()
            entry["status"]="error"
            entry["error"]=str(exc)
            entry["trace"]=tb
            append_log(entry)
            print(f"[ERROR] iteration {iteration} -> logged and continuing. err={exc}")
            # small backoff on error
            time.sleep(2)
        # sleep until next iteration, respecting stop flag
        remaining = ITERATION_S - (time.time() - iter_start)
        if remaining > 0:
            for _ in range(int(max(1, remaining))):
                if _stop: break
                time.sleep(1)
    print("[stability] Run complete or stopped. Exiting.")

def main():
    try:
        run_loop()
    except Exception as e:
        print("[stability] Unhandled exception, logging and exiting:", e)
        append_log({"ts": _now_ts(), "iso": _iso_now(), "status":"fatal","error":str(e)})
    finally:
        print("[stability] Demo terminated.")

if __name__ == "__main__":
    main()
