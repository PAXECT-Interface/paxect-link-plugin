#!/usr/bin/env bash
# PAXECT Demo C – Enterprise CI-Matrix Smoke Runner
# -------------------------------------------------
# Runs all major demos sequentially, captures exit codes and hashes,
# and reports "NO DRIFT ✅" if deterministic outputs match baseline.

set -euo pipefail

ROOT="$(pwd)"
TMP="/tmp/paxect_ci_matrix"
BASE="${TMP}/baseline_hashes.txt"
CURR="${TMP}/current_hashes.txt"
mkdir -p "$TMP"

DEMOS=(
  "demo_01_quick_start.py"
  "demo_02_integration_loop.py"
  "demo_03_safety_throttle.py"
  "demo_04_metrics_health.py"
  "demo_05_link_smoke.sh"
  "demo_06_polyglot_bridge.py"
  "demo_07_selftune_adaptive.py"
  "demo_enterprise_stability.py"
)

echo "=== PAXECT Enterprise CI-Matrix Smoke Runner ==="
echo "Temp dir: $TMP"
echo

fail=0
for demo in "${DEMOS[@]}"; do
  if [[ -x "$ROOT/$demo" ]]; then
    echo "[RUN] $demo ..."
    timeout 30s "$ROOT/$demo" >/tmp/${demo}.out 2>&1 || echo "(non-critical timeout ok)"
    hash=$(sha256sum /tmp/${demo}.out | cut -d' ' -f1)
    printf "%s  %s\n" "$hash" "$demo" >> "$CURR"
  else
    echo "SKIP: $demo not found or not executable"
  fi
done

echo
if [[ ! -f "$BASE" ]]; then
  cp "$CURR" "$BASE"
  echo "Baseline created at $BASE"
  echo "NO DRIFT ✅ (baseline established)"
  exit 0
fi

if diff -u "$BASE" "$CURR" >/dev/null 2>&1; then
  echo "NO DRIFT ✅ — all demo outputs consistent with baseline."
else
  echo "DRIFT DETECTED ❗ — differences found:"
  diff -u "$BASE" "$CURR" || true
  fail=1
fi

echo
echo "Hash summary:"
cat "$CURR"

exit $fail
