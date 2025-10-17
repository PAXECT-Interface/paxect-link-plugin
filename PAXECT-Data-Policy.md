# PAXECT Data Policy

PAXECT enforces a clear policy for maximum data and text size per run. This ensures stable, predictable performance and prevents misuse, in line with industry standards such as Kafka, MQTT, and gRPC.

## 1. Technical Limit

- **Default limit:** Maximum **512 MB** per run or operation.
- **Configurable:** Set a custom limit via environment variable:
  ```bash
  export PAXECT_MAX_INPUT_MB=8192  # For up to 8 GB
  ```
- **Error message when exceeded:**  
  ```
  ❌ Input size exceeds PAXECT policy limit (default 512 MB). Use PAXECT_MAX_INPUT_MB to adjust.
  ```

## 2. Documentation Policy

- This limit applies per operation, plugin, or bridge.
- For larger datasets, use chunking, streaming, or file transfer.
- Some plugins (e.g., Polyglot, AEAD) may have their own limits; see their respective documentation.

## 3. Positioned as a Feature

PAXECT intentionally implements a data size limit, just like other professional data frameworks. This is not a restriction, but a guarantee of reliability, security, and predictable performance.

> _“PAXECT guarantees stable performance up to 512 MB per run. For enterprise workloads, the limit is easily adjustable.”_

---

**Questions or requests? Contact us or open a GitHub issue!**
