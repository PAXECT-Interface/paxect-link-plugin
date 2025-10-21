<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

# PAXECT Data Policy

The **PAXECT Link Plugin** enforces strict data size and transfer limits to ensure  
stable, predictable, and deterministic performance — in line with frameworks  
such as Kafka, MQTT, and gRPC.

---

## 1. Technical Limit

- **Default limit:** Maximum **512 MB** per operation or file relay  
- **Configurable:** Adjustable through environment variable:
  ```bash
  export PAXECT_MAX_INPUT_MB=8192  # For up to 8 GB


 **Error message when exceeded:**

  ```
  ❌ Input size exceeds PAXECT policy limit (default 512 MB). 
  Use PAXECT_MAX_INPUT_MB to adjust.
  ```

---

## 2. Scope & Enforcement

* The limit applies per **encode/decode operation** in the Link plugin
* For larger datasets, use **chunking, streaming, or batched transfer**
* Upstream and downstream components (e.g., Core, AEAD, SelfTune)
  may apply their own limits — see respective documentation
* All relay operations are subject to checksum validation (CRC32 + SHA-256)

---

## 3. Position & Intent

This policy is a **feature**, not a restriction.
Like other deterministic data frameworks, PAXECT sets explicit bounds
to guarantee stability, auditability, and reproducibility.

> *“PAXECT guarantees stable performance up to 512 MB per relay.
> For enterprise workloads, the limit is configurable and deterministic.”*

---

## 4. Data Integrity

* Every frame and output is validated against its checksum
* Failed or oversized transfers are quarantined, never silently dropped
* Optional HMAC manifest verification (`require_sig=true`) adds tamper-resistance
* JSONL logs record all policy decisions and integrity checks

---

## 5. Contact & Questions

For clarification, feature requests, or enterprise extensions:
📧 **enterprise@[PAXECT-Team@outlook.com](mailto:PAXECT-Team@outlook.com)**

---

© 2025 **PAXECT Systems** — All rights reserved.

```



