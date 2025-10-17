#!/usr/bin/env bash
set -e
echo "[DEMO 1] Starting Local Basic Relay…"

export PAXECT_CORE="python3 ../../paxect_core.py"
export PAXECT_LINK_INBOX="./inbox"
export PAXECT_LINK_OUTBOX="./outbox"

mkdir -p inbox outbox
echo "Hello PAXECT!" > inbox/test.txt

# Start relay in background
python3 ../../paxect_link_plugin.py &
PID=$!

# Wacht totdat bestand verschijnt (max 15 seconden)
echo "[DEMO 1] Waiting for relay to process test.txt..."
for i in {1..15}; do
    if [ -f outbox/test.txt ]; then
        echo "[DEMO 1] File received!"
        break
    fi
    sleep 1
done

echo "[DEMO 1] Checking outbox..."
ls -l outbox || true
cat outbox/test.txt || echo "[DEMO 1] No file decoded yet"

kill $PID
echo "[DEMO 1] Done."
