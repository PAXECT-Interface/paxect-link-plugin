#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Demo 3 — Multi-Node Relay (Two Link Instances)
----------------------------------------------
Purpose
--------
Validates deterministic multi-node operation of the PAXECT Link Plugin.
Each node (A/B) runs with its own inbox, outbox, policy, manifest, and lock.

Improvements
------------
- Automatically removes stale .paxect_link.lock files before start
- Uses per-node locks safely
- Waits deterministic 10 s per node
- Prints clear pass/fail summary
- Fully self-cleaning (safe to rerun)

Expected output
---------------
[+] nodeA decoded: ['A']
[+] nodeB decoded: ['B']
✅ Demo 3 complete
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from time import sleep

# === Base setup ===
BASE = Path("/tmp/paxect_demo3")
NODE_A = BASE / "nodeA"
NODE_B = BASE / "nodeB"
for d in [NODE_A, NODE_B]:
    (d / "inbox").mkdir(parents=True, exist_ok=True)
    (d / "outbox").mkdir(parents=True, exist_ok=True)

# Remove stale locks if any
for lf in [NODE_A / ".paxect_link.lock", NODE_B / ".paxect_link.lock"]:
    try:
        lf.unlink()
    except FileNotFoundError:
        pass

# Write sample inputs
(NODE_A / "inbox" / "A.txt").write_text("hello from nodeA\n", encoding="utf-8")
(NODE_B / "inbox" / "B.txt").write_text("hello from nodeB\n", encoding="utf-8")

# === Common policy ===
POLICY = {
    "version": "1.2.0",
    "trusted_nodes": ["localhost", "PAXECT-Interface"],
    "allowed_suffixes": [".txt", ".freq"],
    "max_file_mb": 10,
    "require_sig": False,
    "auto_delete": True,
    "log_level": "info",
}
for node in [NODE_A, NODE_B]:
    (node / "link_policy.json").write_text(json.dumps(POLICY, indent=2))

# === Helper ===
def run_link(node_path: Path, timeout_sec: int = 10):
    """Run a single Link instance with isolated environment."""
    env = os.environ.copy()
    env.update({
        "PAXECT_LINK_INBOX": str(node_path / "inbox"),
        "PAXECT_LINK_OUTBOX": str(node_path / "outbox"),
        "PAXECT_LINK_POLICY": str(node_path / "link_policy.json"),
        "PAXECT_LINK_MANIFEST": str(node_path / "link_manifest.json"),
        "PAXECT_LINK_LOG": str(node_path / "log.jsonl"),
        "PAXECT_LINK_LOCK": str(node_path / ".paxect_link.lock"),
        "PAXECT_CORE": "python3 paxect_core.py",
        "PAXECT_LINK_POLL_SEC": "1.0",
    })

    print(f"\n[+] Starting Link instance → {node_path}")
    try:
        subprocess.run(
            ["python3", "paxect_link_plugin.py"],
            env=env,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"[ℹ] Timeout reached for {node_path.name} after {timeout_sec}s — continuing.\n")

    # Ensure lock cleanup post-run
    try:
        (node_path / ".paxect_link.lock").unlink()
    except FileNotFoundError:
        pass

# === Main ===
def main():
    print("=== Demo 3 — Multi-Node Relay Simulation (start) ===")

    # Node A
    run_link(NODE_A, timeout_sec=10)
    sleep(2)

    # Node B
    run_link(NODE_B, timeout_sec=10)

    # Verify results
    decoded_a = [p.name for p in (NODE_A / "outbox").glob("*") if p.is_file()]
    decoded_b = [p.name for p in (NODE_B / "outbox").glob("*") if p.is_file()]

    print(f"[+] nodeA decoded: {decoded_a or '— nothing —'}")
    print(f"[+] nodeB decoded: {decoded_b or '— nothing —'}")

    if decoded_a and decoded_b:
        print("✅ Demo 3 complete\n")
    else:
        print("⚠️ Demo 3 incomplete — inspect logs under /tmp/paxect_demo3/*/log.jsonl\n")

    # Cleanup (safe)
    try:
        shutil.rmtree(BASE)
    except Exception:
        pass


if __name__ == "__main__":
    main()
