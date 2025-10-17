### 📡 Data Policy (Transmission & Stability)

PAXECT Link Plugin applies a controlled data-size limit per relay cycle to ensure cross-OS stability and prevent I/O overload.

**Default limit:** 512 MB per relay job  
**Adjustable:** `export PAXECT_MAX_INPUT_MB=8192`

> “Each link cycle guarantees predictable latency and zero-loss relay up to 512 MB.  
> For enterprise relay networks, increase the limit as needed.”

Use inbox/outbox rotation or streaming channels for multi-GB payloads.
