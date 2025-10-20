#!/usr/bin/env python3
"""
PAXECT Demo 08 – Secure Multi-Channel AEAD-Hybrid Bridge
--------------------------------------------------------
Full demonstration of the AEAD-Hybrid plugin concept:
  • Hybrid AES-GCM / ChaCha20-Poly1305 simulation
  • Multi-channel encryption (data / control / heartbeat)
  • Deterministic, offline-first operation
  • Adaptive SelfTune epsilon adjustment
  • Cross-OS reproducibility (no external dependencies)

This demo is symbolic: it shows hybrid key-wrapping and AEAD
authentication in action, without relying on external crypto libs.
"""

import json, hashlib, base64, random, tempfile, time
from pathlib import Path

# --------------------------------------------------------------------
# Config / state
# --------------------------------------------------------------------
STATE = Path(tempfile.gettempdir()) / "paxect_demo_08_state.json"
CHANNELS = ["data", "control", "heartbeat"]

# Hybrid keypair (simulated deterministic AES+ChaCha engine)
PRIVATE_KEY = hashlib.sha256(b"PAXECT-HYBRID-PRIVATE").digest()
PUBLIC_KEY  = hashlib.sha256(b"PAXECT-HYBRID-PUBLIC").digest()

# --------------------------------------------------------------------
# Core hybrid AEAD functions
# --------------------------------------------------------------------
def hybrid_wrap_key(sym_key: bytes) -> str:
    """Simulate wrapping symmetric key with a public key (AES-GCM/ChaCha hybrid)."""
    wrapped = bytes(a ^ b for a, b in zip(sym_key, PUBLIC_KEY))
    return base64.b64encode(wrapped).decode()

def hybrid_unwrap_key(wrapped_b64: str) -> bytes:
    """Simulate unwrapping with private key."""
    wrapped = base64.b64decode(wrapped_b64)
    unwrapped = bytes(a ^ b for a, b in zip(wrapped, PUBLIC_KEY))
    return unwrapped

def aead_encrypt(channel: str, plaintext: str, key: bytes):
    """Simulate AEAD (AES-GCM / ChaCha20-Poly1305) encryption."""
    nonce = hashlib.sha256((channel + "nonce").encode()).digest()[:12]
    cipher = base64.b64encode(bytes(a ^ b for a, b in zip(plaintext.encode(), key * 8))).decode()
    tag = hashlib.sha256((cipher + channel).encode()).hexdigest()[:16]
    algo = "AES-GCM" if int.from_bytes(nonce[:1], "big") % 2 == 0 else "ChaCha20-Poly1305"
    return {"algo": algo, "nonce": base64.b64encode(nonce).decode(),
            "cipher": cipher, "tag": tag}

def aead_decrypt(channel: str, packet: dict, key: bytes):
    """Verify tag and decrypt."""
    check = hashlib.sha256((packet["cipher"] + channel).encode()).hexdigest()[:16]
    ok = check == packet["tag"]
    plain = bytes(a ^ b for a, b in zip(base64.b64decode(packet["cipher"]), key * 8))
    return plain.decode(errors="ignore"), ok, packet["algo"]

# --------------------------------------------------------------------
# Demo logic
# --------------------------------------------------------------------
def main():
    print("=== PAXECT Demo 08 – Secure Multi-Channel AEAD-Hybrid Bridge ===")
    state = json.loads(STATE.read_text()) if STATE.exists() else {"cycle": 0, "epsilon": 0.1}
    eps = state["epsilon"]
    mode = "exploit" if random.random() > eps else "explore"
    state["cycle"] += 1
    print(f"Cycle {state['cycle']} | mode={mode} | epsilon={eps}")

    results = []
    for ch in CHANNELS:
        # Generate symmetric session key for this channel
        sym_key = hashlib.sha256(f"{ch}-{state['cycle']}".encode()).digest()
        wrapped = hybrid_wrap_key(sym_key)
        unwrapped = hybrid_unwrap_key(wrapped)
        enc = aead_encrypt(ch, f"{ch}-payload-{state['cycle']}", unwrapped)
        dec, ok, algo = aead_decrypt(ch, enc, unwrapped)
        match = dec == f"{ch}-payload-{state['cycle']}"
        results.append({
            "channel": ch,
            "algorithm": algo,
            "wrapped_key_len": len(wrapped),
            "aead_ok": ok,
            "match": match
        })

    # Adaptive SelfTune
    success = all(r["match"] for r in results)
    eps = round(max(0.05, eps * 0.95) if success else min(0.5, eps + 0.05), 3)
    state["epsilon"] = eps
    STATE.write_text(json.dumps(state))

    digest = hashlib.sha256(json.dumps(results, sort_keys=True).encode()).hexdigest()[:12]
    summary = {
        "cycle": state["cycle"],
        "epsilon": eps,
        "mode": mode,
        "digest": digest,
        "channels": results,
        "status": "All hybrid channels synchronized ✅" if success else "Drift detected ❗"
    }
    print(json.dumps(summary, indent=2))
    print(f"\nState saved to: {STATE}")
    print("Hybrid AES-GCM / ChaCha20-Poly1305 simulation complete.\n")

if __name__ == "__main__":
    main()
