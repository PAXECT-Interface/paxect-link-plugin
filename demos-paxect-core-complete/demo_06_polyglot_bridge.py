#!/usr/bin/env python3
"""
PAXECT Demo 06 – Polyglot Bridge
--------------------------------
Simulates data exchange between PAXECT Core and an external language/runtime.

Steps:
 1. Encode sample data (simulate core encode)
 2. "Foreign system" transforms it (mocked)
 3. Decode back and verify deterministic output
 4. Compare checksums – no drift expected
"""

import hashlib, base64, json, time, tempfile
from pathlib import Path

DATA_SAMPLE = "PAXECT–Polyglot–Bridge–Test"
TMP_PATH = Path(tempfile.gettempdir()) / "paxect_demo_06_polyglot.json"

def encode_core(data: str) -> str:
    """Simulate PAXECT Core encode (base64 + hash footer)."""
    encoded = base64.b64encode(data.encode()).decode()
    checksum = hashlib.sha256(data.encode()).hexdigest()
    packet = {"encoded": encoded, "checksum": checksum}
    TMP_PATH.write_text(json.dumps(packet))
    return checksum

def foreign_system_process():
    """Simulate external system (e.g., JS/Rust) loading & returning packet."""
    time.sleep(0.2)
    packet = json.loads(TMP_PATH.read_text())
    # simulate harmless transformation (e.g., newline normalization)
    packet["encoded"] = packet["encoded"].replace("\n", "")
    TMP_PATH.write_text(json.dumps(packet))

def decode_core() -> dict:
    """Decode back and verify checksum."""
    packet = json.loads(TMP_PATH.read_text())
    decoded = base64.b64decode(packet["encoded"]).decode()
    checksum = hashlib.sha256(decoded.encode()).hexdigest()
    return {
        "decoded": decoded,
        "checksum_match": checksum == packet["checksum"],
        "checksum": checksum
    }

def main():
    print("=== PAXECT Demo 06 – Polyglot Bridge ===")
    orig_hash = encode_core(DATA_SAMPLE)
    foreign_system_process()
    result = decode_core()

    summary = {
        "original_checksum": orig_hash,
        "decoded_checksum": result["checksum"],
        "checksum_match": result["checksum_match"],
        "decoded": result["decoded"]
    }

    print(json.dumps(summary, indent=2))
    if result["checksum_match"]:
        print("\nNO DRIFT ✅ — Cross-system integrity verified.")
    else:
        print("\nDRIFT DETECTED ❗ — checksum mismatch.")

if __name__ == "__main__":
    main()
