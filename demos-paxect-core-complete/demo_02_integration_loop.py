#!/usr/bin/env python3
"""
PAXECT Demo 02 – Integration Loop
---------------------------------
Simulates an application loop calling the SelfTune plugin repeatedly.

Goals:
- Perform 10 adaptive cycles (exploit/explore)
- Aggregate results and success ratio
- Write summary JSONL to /tmp
"""

import json, random, time, tempfile
from pathlib import Path

CYCLES = 10
EPSILON = 0.1
LOG_PATH = Path(tempfile.gettempdir()) / "paxect_demo_02_integration_loop.jsonl"

def simulate_selftune_cycle(cycle_id):
    """Run one adaptive step (simulate epsilon-greedy)."""
    mode = "explore" if random.random() < EPSILON else "exploit"
    reward = random.uniform(0.8, 1.0) if mode == "exploit" else random.uniform(0.0, 1.0)
    result = {
        "cycle": cycle_id,
        "mode": mode,
        "reward": round(reward, 3),
        "timestamp": int(time.time())
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(result) + "\n")
    return result

def main():
    print("=== PAXECT Demo 02 – Integration Loop ===")
    all_results = []
    for i in range(1, CYCLES + 1):
        res = simulate_selftune_cycle(i)
        all_results.append(res)
        print(f"[cycle {i:02d}] mode={res['mode']} reward={res['reward']}")
        time.sleep(0.2)  # simulate workload delay

    # Aggregate statistics
    exploit_count = sum(1 for r in all_results if r["mode"] == "exploit")
    explore_count = CYCLES - exploit_count
    avg_reward = round(sum(r["reward"] for r in all_results) / CYCLES, 3)
    summary = {
        "cycles": CYCLES,
        "exploit": exploit_count,
        "explore": explore_count,
        "avg_reward": avg_reward,
        "log_path": str(LOG_PATH)
    }

    print(json.dumps(summary, indent=2))
    print("\n[OK] Demo 02 finished successfully")

if __name__ == "__main__":
    main()
