#!/usr/bin/env python3
"""
PAXECT Demo 03 – Safety & Throttle Test
---------------------------------------
Simulates repeated operation attempts with two time-based throttles:
 - short window (e.g. 5s default, set THROTTLE_SHORT_S)
 - long window  (e.g. 15s default, set THROTTLE_LONG_S)

Persistent JSON state is stored under a temp file so counts survive restarts.
This allows you to test cooldowns, limits and reset behavior.

Run:
  chmod +x demo_03_safety_throttle.py
  python3 demo_03_safety_throttle.py

Env vars (optional):
  THROTTLE_SHORT_S   (default 5)    - short time window seconds (dev-friendly)
  THROTTLE_SHORT_LIM (default 3)    - max ops allowed in short window
  THROTTLE_LONG_S    (default 15)   - long time window seconds (dev-friendly)
  THROTTLE_LONG_LIM  (default 8)    - max ops allowed in long window
  ATTEMPTS           (default 20)   - number of attempts to simulate
"""

import os
import time
import json
import tempfile
from pathlib import Path
from collections import deque

# Config (override with env vars)
SHORT_S = int(os.environ.get("THROTTLE_SHORT_S", "5"))
SHORT_LIM = int(os.environ.get("THROTTLE_SHORT_LIM", "3"))
LONG_S = int(os.environ.get("THROTTLE_LONG_S", "15"))
LONG_LIM = int(os.environ.get("THROTTLE_LONG_LIM", "8"))
ATTEMPTS = int(os.environ.get("ATTEMPTS", "20"))

STATE_PATH = Path(tempfile.gettempdir()) / "paxect_demo_03_throttle_state.json"

def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            return {}
    return {}

def save_state(state):
    try:
        STATE_PATH.write_text(json.dumps(state))
    except Exception:
        pass

def now():
    return int(time.time())

class ThrottleWindow:
    def __init__(self, window_s, limit, history=None):
        self.window_s = int(window_s)
        self.limit = int(limit)
        # Use deque of timestamps for sliding window
        self.hits = deque(history if history else [])

    def allow(self, ts):
        # Remove old
        cutoff = ts - self.window_s
        while self.hits and self.hits[0] <= cutoff:
            self.hits.popleft()
        if len(self.hits) < self.limit:
            self.hits.append(ts)
            return True
        return False

    def to_list(self):
        return list(self.hits)

def run_simulation(attempts, short_s, short_lim, long_s, long_lim):
    state = load_state()
    # restore history arrays if present
    short_hist = deque(state.get("short_hist", []))
    long_hist = deque(state.get("long_hist", []))

    short = ThrottleWindow(short_s, short_lim, history=short_hist)
    long = ThrottleWindow(long_s, long_lim, history=long_hist)

    results = []
    print("=== PAXECT Demo 03 – Safety & Throttle Test ===")
    print(f"SHORT window: {short_s}s limit={short_lim}  |  LONG window: {long_s}s limit={long_lim}")
    print(f"State file: {STATE_PATH}\n")

    for i in range(1, attempts + 1):
        ts = now()
        allowed_short = short.allow(ts)
        allowed_long = long.allow(ts)
        allowed = allowed_short and allowed_long

        status = "ALLOWED" if allowed else "THROTTLED"
        reason = []
        if not allowed_short:
            reason.append("short-limit")
        if not allowed_long:
            reason.append("long-limit")

        rec = {
            "attempt": i,
            "ts": ts,
            "status": status,
            "reason": ",".join(reason) if reason else None,
            "short_count": len(short.hits),
            "long_count": len(long.hits),
        }
        results.append(rec)
        print(f"[{i:02d}] {status:8}  short={rec['short_count']:2d}/{short_lim}  long={rec['long_count']:2d}/{long_lim}  reason={rec['reason']}")
        # small sleep to create spread (fast dev test)
        time.sleep(0.5)

    # persist history
    final_state = {
        "short_hist": short.to_list(),
        "long_hist": long.to_list(),
        "last_run_ts": now(),
    }
    save_state(final_state)

    print("\nSummary:")
    allowed_total = sum(1 for r in results if r["status"] == "ALLOWED")
    throttled_total = len(results) - allowed_total
    print(f"Total attempts: {len(results)}  Allowed: {allowed_total}  Throttled: {throttled_total}")
    print(f"Persisted state to: {STATE_PATH}")
    return results

def main():
    run_simulation(ATTEMPTS, SHORT_S, SHORT_LIM, LONG_S, LONG_LIM)

if __name__ == "__main__":
    main()
