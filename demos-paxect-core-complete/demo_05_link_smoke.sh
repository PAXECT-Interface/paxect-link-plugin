#!/usr/bin/env bash
# PAXECT Demo 05 — Link Smoke Test
# Usage:
#   chmod +x demo_05_link_smoke.sh
#   ./demo_05_link_smoke.sh
#
# What it does:
# - Ensures key files exist
# - Fixes line endings (optional, if dos2unix present)
# - Makes main scripts executable
# - Checks basic inbox/outbox dirs for Link plugin
# - Computes SHA256 of key files and compares with baseline (/tmp/paxect_link_hashes.baseline)
# - Prints NO DRIFT ✅ if hashes match, otherwise shows diffs

set -u

ROOT_DIR="$(pwd)"
TMP_BASE="/tmp/paxect_demo_05"
BASEFILE="${TMP_BASE}/paxect_link_hashes.baseline"
mkdir -p "${TMP_BASE}"

# Files to include in hash-check (adjust names if your files are elsewhere)
FILES=(
  "paxect_link_plugin.py"
  "paxect_core.py"
  "paxect_aead_hybrid_plugin.py"
  "paxect_polyglot_plugin.py"
  "paxect_selftune_plugin.py"
)

echo "=== PAXECT Demo 05 — Link Smoke Test ==="
echo "Working dir: ${ROOT_DIR}"
echo

# 1) Verify files exist
missing=0
for f in "${FILES[@]}"; do
  if [ ! -f "${f}" ]; then
    echo "MISSING: ${f}"
    missing=$((missing+1))
  else
    echo "FOUND : ${f}"
  fi
done

if [ "${missing}" -gt 0 ]; then
  echo
  echo "ERROR: ${missing} files missing. Place them in the current directory and re-run."
  exit 1
fi

echo
# 2) Normalize line endings if dos2unix available
if command -v dos2unix >/dev/null 2>&1; then
  echo "dos2unix: normalizing line endings for script files..."
  for f in "${FILES[@]}"; do
    dos2unix -q "${f}" || true
  done
else
  echo "dos2unix not found — skipping line ending normalization (ok on Unix systems)."
fi

echo
# 3) Make main scripts executable
echo "Setting +x on detected script files..."
for f in "${FILES[@]}"; do
  chmod +x "${f}" || true
done
echo "Done."

echo
# 4) Check Link plugin default dirs (heuristic from demo)
LINK_INBOX="${HOME}/inbox"
LINK_OUTBOX="${HOME}/outbox"
LINK_POLICY="${HOME}/link_policy.json"

echo "Checking link paths:"
[ -d "${LINK_INBOX}" ] && echo "Inbox exists: ${LINK_INBOX}" || echo "Inbox missing: ${LINK_INBOX} (ok if not used)"
[ -d "${LINK_OUTBOX}" ] && echo "Outbox exists: ${LINK_OUTBOX}" || echo "Outbox missing: ${LINK_OUTBOX} (ok if not used)"
[ -f "${LINK_POLICY}" ] && echo "Policy file exists: ${LINK_POLICY}" || echo "Policy file missing: ${LINK_POLICY} (ok if not used)"

echo
# 5) Compute current hashes
HASHFILE="${TMP_BASE}/current_hashes.txt"
echo "Computing SHA256 of files..."
> "${HASHFILE}"
for f in "${FILES[@]}"; do
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${f}" >> "${HASHFILE}"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "${f}" >> "${HASHFILE}"
  else
    # fallback to Python if neither tool exists
    python3 - <<PY >> "${HASHFILE}"
import hashlib,sys
fn=sys.argv[1]
h=hashlib.sha256(open(fn,'rb').read()).hexdigest()
print(h + "  " + fn)
PY
  fi
done
echo "Hashes written to: ${HASHFILE}"

echo
# 6) Compare with baseline (or create baseline if missing)
if [ ! -f "${BASEFILE}" ]; then
  cp "${HASHFILE}" "${BASEFILE}"
  echo "Baseline created at ${BASEFILE} (first run)."
  echo "NO DRIFT ✅ (baseline established)."
  exit 0
fi

echo "Comparing with baseline ${BASEFILE} ..."
if diff -u "${BASEFILE}" "${HASHFILE}" >/dev/null 2>&1; then
  echo "NO DRIFT ✅ — current file hashes match baseline."
  exit 0
else
  echo "DRIFT DETECTED ❗ — file hash differences:"
  diff -u "${BASEFILE}" "${HASHFILE}" || true
  echo
  echo "If these changes are expected, update baseline with:"
  echo "  cp ${HASHFILE} ${BASEFILE}"
  exit 2
fi
