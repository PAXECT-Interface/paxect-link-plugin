

---

# PAXECT Link — Test Demos (1–5)

This README explains how to run the enterprise demos for **PAXECT Core** and **PAXECT Link Plugin**.
All demos are local-only, zero telemetry, and rely on the Python standard library (Core additionally needs `zstandard` and `psutil`).

## Prerequisites

* **Python**: 3.8+ (tested on 3.12)
* **Packages**: `zstandard`, `psutil`
* **OS**: Linux/Ubuntu (other OSes should work; paths may differ)

> Debian/Ubuntu with PEP 668: use a virtualenv.

```bash
python3 -m venv ~/.venvs/paxect
source ~/.venvs/paxect/bin/activate
python -m pip install --upgrade pip
pip install zstandard psutil
```

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
   └─ demo_5_ci_cd_pipeline.py
```

## Quick sanity check

```bash
python paxect_core.py -h
python paxect_link_plugin.py -h || true     # prints startup banner when run
```

---

## Demo 1 — Local Basic Relay

**Goal:** Sanity-check encode → decode via PAXECT Core + Link.
**What it does:** Puts `example.txt` in an inbox, Link encodes to `.freq`, decodes to outbox.

```bash
python demos/demo_1_local_basic.py
```

**Expected output:** `decoded: ['example']` and `✅ Demo 1 complete`.

---

## Demo 2 — Policy + HMAC Enforcement

**Goal:** Require signed peer manifests; accept signed, reject unsigned.
**What it does:** Writes one valid HMAC-signed manifest (`node2`) and one invalid (`evil`).

```bash
python demos/demo_2_policy_hmac.py
```

**Expected output:** `decoded: ['contract']`, plus log lines showing `handshake` (accepted) and `handshake_reject` (bad_sig).
**Tip:** HMAC key is injected via `PAXECT_LINK_HMAC_KEY`.

---

## Demo 3 — Multi-Node (Two Link Instances)

**Goal:** Run two Link instances (`nodeA`, `nodeB`) with signed manifests and per-node locks.
**What it does:** Each node encodes its own file and decodes to its own outbox.

```bash
python demos/demo_3_multi_node.py
```

**Expected output:**
`[+] nodeA decoded: ['A']` and `[+] nodeB decoded: ['B']`, plus handshake lines for both nodes.

---

## Demo 4 — Observability (JSONL → metrics)

**Goal:** Show how to turn JSONL logs into simple metrics.
**What it does:** Processes two allowed inputs (`ok1.txt`, `ok2.csv`) and one blocked (`blocked.exe`); prints event counters and recent log lines.

```bash
python demos/demo_4_observability.py
```

**Expected output:**

* `Decoded files: 2`
* `Policy blocks: 1` (the `.exe`), plus a short event/level summary.

---

## Demo 5 — CI/CD Pipeline Smoke (JUnit XML)

**Goal:** Minimal smoke suite for CI:

1. Core encode/decode roundtrip
2. Link relay success
   **What it does:** Emits a JUnit XML at `/tmp/paxect_demo5/junit_smoke.xml`.

```bash
python demos/demo_5_ci_cd_pipeline.py ; echo "exit=$?"
```

**Expected output:**

* `PASS - core_encode`, `PASS - core_decode_verify`, `PASS - link_relay_decoded`
* `exit=0` and the JUnit file path.

---

## Environment variables (Link)

| Variable               | Purpose                                          | Example                         |
| ---------------------- | ------------------------------------------------ | ------------------------------- |
| `PAXECT_LINK_INBOX`    | Directory to watch for inputs                    | `/tmp/paxect_demo*/inbox`       |
| `PAXECT_LINK_OUTBOX`   | Directory to write decoded outputs               | `/tmp/paxect_demo*/outbox`      |
| `PAXECT_LINK_POLICY`   | JSON policy file                                 | `/tmp/paxect_demo*/policy.json` |
| `PAXECT_LINK_LOG`      | JSONL log file                                   | `/tmp/paxect_demo*/log.jsonl`   |
| `PAXECT_LINK_MANIFEST` | Self manifest path (for peer discovery)          | `/tmp/.../link_manifest.json`   |
| `PAXECT_LINK_HMAC_KEY` | HMAC key (hex/utf-8 string) for signed manifests | `supersecret-demo-hmac-key`     |
| `PAXECT_LINK_LOCK`     | Lock file path (set per-node in Demo 3)          | `/tmp/.../.paxect_link.lock`    |
| `PAXECT_CORE`          | How to invoke PAXECT Core                        | `python paxect_core.py`         |
| `PAXECT_LINK_POLL_SEC` | Polling interval (seconds)                       | `2.0`                           |

---

## Policy tips

* **trusted_nodes** must include your actual hostname (e.g., `PAXECT-Interface`) or use `localhost` when appropriate.
* **allowed_suffixes** should include `.freq` (containers) and sidecar files are auto-managed.
* Setting `require_sig: true` enables HMAC verification. Unsigned/invalid peer manifests will be rejected.

---

## Troubleshooting

* **Policy blocks (untrusted_node: …)**
  Add your hostname to `trusted_nodes`.
* **Two Link instances, one exits**
  Use **per-node lock** via `PAXECT_LINK_LOCK` (Demo 3 already does this).
* **PEP 668 errors on Ubuntu**
  Use a virtualenv as shown in *Prerequisites*.
* **No output in outbox**
  Check the JSONL log (`…/log.jsonl`) for `policy_block`, `encode_error`, or `decode_error`.

---

## License

All demo scripts and plugins: **Apache-2.0** (see file headers).
