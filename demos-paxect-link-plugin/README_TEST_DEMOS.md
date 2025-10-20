

# PAXECT Link — Test Demos (1–6)

This README explains how to run the enterprise demos for **PAXECT Core** and **PAXECT Link Plugin**.
All demos are local-only, zero telemetry, and rely on the Python standard library
(Core additionally needs `zstandard` and `psutil`).

---

## Prerequisites

* **Python**       : 3.8 +  (tested on 3.12)
* **Packages**    : `zstandard`, `psutil`
* **OS**          : Linux / Ubuntu (others work; paths may differ)

> Debian/Ubuntu with PEP 668: use a virtual environment.

```bash
python3 -m venv ~/.venvs/paxect
source ~/.venvs/paxect/bin/activate
python -m pip install --upgrade pip
pip install zstandard psutil
```

---

## Repository layout

```
repo/
├─ paxect_core.py
├─ paxect_link_plugin.py
└─ demos/
   ├─ demo_1_local_basic.py
   ├─ demo_2_policy_hmac.py
   ├─ demo_3_multi_node.py
   ├─ demo_4_observability.py
   ├─ demo_5_ci_cd_pipeline.py
   └─ demo_6_fail_and_recover.py
```

---

## Quick sanity check

```bash
python paxect_core.py -h
python paxect_link_plugin.py -h || true
```

---

## Demo 1 — Local Basic Relay

**Goal:** Verify end-to-end encode → decode using Core + Link.
**What it does:** Places `example.txt` in the inbox; Link encodes to `.freq`, then decodes to the outbox.

```bash
python demos/demo_1_local_basic.py
```

**Expected output:** `decoded: ['example']` and `✅ Demo 1 complete`.

---

## Demo 2 — Policy + HMAC Enforcement

**Goal:** Require signed peer manifests and reject unsigned ones.
**What it does:** Writes one valid HMAC-signed manifest (`node2`) and one invalid (`evil`).

```bash
python demos/demo_2_policy_hmac.py
```

**Expected output:** `decoded: ['contract']`, plus log entries showing
`handshake` (accepted) and `handshake_reject` (bad signature).
**Tip:** Set `PAXECT_LINK_HMAC_KEY` to the expected key.

---

## Demo 3 — Multi-Node (Two Link Instances)

**Goal:** Run two Link instances (`nodeA`, `nodeB`) with per-node locks and signed manifests.
**What it does:** Each node encodes its own file and decodes to its own outbox.

```bash
python demos/demo_3_multi_node.py
```

**Expected output:**

```
[+] nodeA decoded: ['A']
[+] nodeB decoded: ['B']
✅ Demo 3 complete
```

Both instances run in sequence without conflict, demonstrating safe multi-process isolation.

---

## Demo 4 — Observability (JSONL → Metrics)

**Goal:** Show how to turn JSONL logs into basic metrics.
**What it does:** Processes two allowed inputs (`ok1.txt`, `ok2.csv`) and one blocked (`blocked.exe`);
prints event counts and log summary.

```bash
python demos/demo_4_observability.py
```

**Expected output:**

* `Decoded files: 2`
* `Policy blocks: 1` (the `.exe`) plus short event summary.

---

## Demo 5 — CI/CD Pipeline Smoke (Enterprise Hardened)

**Goal:** Validate that **PAXECT Core** and **PAXECT Link Plugin** operate deterministically and are CI-ready.
**What it does:**

1. Runs a Core encode → decode roundtrip for bit-identical verification.
2. Starts a local Link relay with minimal JSON policy.
3. Automatically cleans old locks before and after run.
4. Generates a JUnit XML report at `/tmp/paxect_demo5/junit_smoke.xml`.

```bash
python demos/demo_5_ci_cd_pipeline.py ; echo "exit=$?"
```

**Expected output:**

```
=== Demo 5 — CI/CD Smoke Suite (Enterprise Hardened) ===
PASS - core_encode_decode
PASS - link_relay_decoded
JUnit report written to: /tmp/paxect_demo5/junit_smoke.xml
exit=0
✅ Demo 5 complete
```

**Notes:**

* Automatically removes stale `.paxect_link.lock` files.
* Offline-first, zero telemetry.
* CI systems can parse `junit_smoke.xml` for automated dashboards.

---

## Demo 6 — Fail & Self-Recover (Resilient Relay)

**Goal:** Demonstrate that the Link Plugin detects and recovers from failures autonomously.
**What it does:**

1. Places two files in the inbox — one valid (`ok.txt`) and one corrupted (`bad.freq` + bad checksum).
2. The plugin logs `checksum_mismatch` and `policy_block` events for the corrupted file.
3. It waits according to `PAXECT_LINK_BACKOFF_SEC`, then continues processing healthy files.
4. Produces a structured JSONL log showing errors followed by recovery.

```bash
python demos/demo_6_fail_and_recover.py
```

**Expected output:**

```
=== Demo 6 — Fail & Self-Recover ===
Injecting 1 valid and 1 corrupted file...
[LINK] checksum_mismatch ... sidecar sha256 mismatch
[LINK] policy_block ... disallowed_suffix:.sha256
[+] Outbox files: ['ok']
✅ Self-recovery confirmed — system continued after failure.
```

**Takeaway:**
The Link Plugin never crashes on corrupted inputs — it detects, logs, backs off, and recovers automatically.
This demonstrates enterprise-grade resilience and observability.

---

## Environment variables (Link)

| Variable                  | Purpose                                            | Example                         |
| ------------------------- | -------------------------------------------------- | ------------------------------- |
| `PAXECT_LINK_INBOX`       | Directory to watch for inputs                      | `/tmp/paxect_demo*/inbox`       |
| `PAXECT_LINK_OUTBOX`      | Directory to write decoded outputs                 | `/tmp/paxect_demo*/outbox`      |
| `PAXECT_LINK_POLICY`      | JSON policy file                                   | `/tmp/paxect_demo*/policy.json` |
| `PAXECT_LINK_LOG`         | JSONL log file                                     | `/tmp/paxect_demo*/log.jsonl`   |
| `PAXECT_LINK_MANIFEST`    | Self manifest path (for peer discovery)            | `/tmp/.../link_manifest.json`   |
| `PAXECT_LINK_HMAC_KEY`    | HMAC key (hex / utf-8 string) for signed manifests | `supersecret-demo-hmac-key`     |
| `PAXECT_LINK_LOCK`        | Lock file path (per-node)                          | `/tmp/.../.paxect_link.lock`    |
| `PAXECT_CORE`             | How to invoke PAXECT Core                          | `python paxect_core.py`         |
| `PAXECT_LINK_POLL_SEC`    | Polling interval (seconds)                         | `2.0`                           |
| `PAXECT_LINK_BACKOFF_SEC` | Retry delay after failure (seconds)                | `2.0`                           |

---

## Policy tips

* Ensure your **hostname** (e.g., `PAXECT-Interface`) is listed in `trusted_nodes`.
* Include `.freq` in `allowed_suffixes`.
* Set `require_sig: true` to enforce HMAC verification.
* Unsigned or invalid peer manifests will be rejected automatically.

---

## Troubleshooting

* **Policy blocks (untrusted_node)** → add your hostname to `trusted_nodes`.
* **Two Link instances, one exits** → use unique lock files (per-node).
* **PEP 668 errors on Ubuntu** → use a virtual environment.
* **No output in outbox** → check the JSONL log for `policy_block`, `encode_error`, or `decode_error`.
* **Corrupted input tests (Demo 6)** → look for `checksum_mismatch` followed by normal `decode` events.

---

## License

All demo scripts and plugins are released under **Apache-2.0** (see file headers).

---

✅ **PAXECT Link Plugin Demo Suite Complete — Enterprise-Ready (1 – 6)**

