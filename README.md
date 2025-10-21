<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---

[![Star this repo](https://img.shields.io/badge/⭐%20Star-this%20repo-orange)](../../stargazers)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](../../actions)
[![CodeQL](https://img.shields.io/badge/CodeQL-active-lightgrey.svg)](../../actions)
[![Issues](https://img.shields.io/badge/Issues-open-blue)](../../issues)
[![Discussions](https://img.shields.io/badge/Discuss-join-blue)](../../discussions)
[![Security](https://img.shields.io/badge/Security-responsible%20disclosure-informational)](./SECURITY.md)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
<a href="https://github.com/PAXECT-Interface/paxect-link-plugin/releases/latest">
  <img alt="Release" src="https://img.shields.io/github/v/release/PAXECT-Interface/paxect-link-plugin?label=link">
</a>

---

# 🔗 **PAXECT Link — Deterministic Inbox/Outbox Bridge**

> Status: **v1.0.0 — Initial Public Release** (see Releases)

Secure, deterministic file relay across processes, runtimes, and operating systems — fully **offline**.
The **PAXECT Link Plugin** provides a reproducible, verifiable bridge by auto-encoding non-`.freq` files **to** `.freq` and auto-decoding `.freq` containers **to** raw files, powered by **PAXECT Core**.

Plug-and-play with zero dependencies and no vendor lock-in.

No cloud, no AI heuristics — just **byte-for-byte deterministic transport**.

---

## 🧩 Overview

PAXECT Link is a **shared-folder bridge** enabling **lossless and reproducible** file exchange between heterogeneous systems.
It ensures that binary and textual data remain **bit-identical** when transferred across languages, platforms, and operating systems.

Unlike ad-hoc watchers or fragile serialization layers, Link uses the **PAXECT Core container format** with CRC32 + SHA-256 to guarantee **checksum-verified integrity** and **perfect reproducibility**.

It serves as the glue between analytical systems, edge devices, and enterprise runtimes — enabling deterministic exchange without sockets or servers.

---

## ⚙️ Key Features

* 🔄 **Deterministic Relay** — auto-encode non-`.freq` → `.freq`, auto-decode `.freq` → files
* 🔐 **Integrity-Checked Transport** — CRC32 per frame + SHA-256 footer verification
* 🧠 **No-AI / No-Heuristics Policy** — deterministic, auditable behavior
* 🧰 **Self-Contained** — Link is stdlib-only; Core is a single Python CLI
* 💻 **Cross-OS Reproducibility** — identical output on Linux · macOS · Windows
* 🛡️ **Policy Enforcement** — trusted nodes, allowed suffixes, max file size
* ✍️ **HMAC-Trusted Manifests (optional)** — `require_sig=true` for peer discovery
* 💥 **Crash-Safe I/O** — atomic `.part → fsync → rename`, single-instance lock

---

## 🌍 Supported Languages & Platforms

**Operating Systems**

| Supported                         | Architecture  |
| --------------------------------- | ------------- |
| Linux (Ubuntu, Debian, Fedora)    | x86_64, ARMv8 |
| Windows 10/11                     | x86_64        |
| macOS 13+ (Intel & Apple Silicon) | arm64, x86_64 |
| FreeBSD / OpenBSD                 | Experimental  |
| RISC-V                            | Planned       |

**Languages**

| Tier            | Runtimes                                                                                |
| --------------- | --------------------------------------------------------------------------------------- |
| **Official**    | Python (Link + Core)                                                                    |
| **Also Tested** | Shell scripts, Node.js, Go, Rust, Java, C/C++, Swift (via Core CLI piping where needed) |

---

## 🧠 Core Capabilities

| Capability                     | Description                                      |
| ------------------------------ | ------------------------------------------------ |
| **Deterministic Encoding**     | Bit-identical PAXECT containers across platforms |
| **Secure Hash Validation**     | CRC32 per frame + SHA-256 of original data       |
| **Cross-Runtime Adaptability** | Works via stdin/stdout piping with any runtime   |
| **Containerized Protocol**     | Fixed header/footer; multi-channel frames (Core) |
| **Offline Operation**          | No network or telemetry; local-only              |

---


## 🚀 Demos Included

All demos are deterministic, self-contained, and safe to run locally or in CI.

| Demo | Script                       | Description                                              | Status |
| ---- | ---------------------------- | -------------------------------------------------------- | ------ |
| 01   | `demo_1_local_basic.py`      | Local encode→decode sanity check                         | ✅      |
| 02   | `demo_2_policy_hmac.py`      | Policy with HMAC: accept signed, reject unsigned         | ✅      |
| 03   | `demo_3_multi_node.py`       | Two Link nodes, per-node lock, both decode               | ✅      |
| 04   | `demo_4_observability.py`    | JSONL logs → simple metrics summary                      | ✅      |
| 05   | `demo_5_ci_cd_pipeline.py`   | CI smoke; emits JUnit XML                                | ✅      |
| 06   | `demo_6_fail_and_recover.py` | Simulated failure & automatic recovery (resilience test) | ✅      |

Run all demos sequentially:

```bash
python3 demos/demo_1_local_basic.py
python3 demos/demo_2_policy_hmac.py
python3 demos/demo_3_multi_node.py
python3 demos/demo_4_observability.py
python3 demos/demo_5_ci_cd_pipeline.py
python3 demos/demo_6_fail_and_recover.py
```

---

## 🧩 Architecture Overview

```text
paxect-link-plugin/
├── paxect_link_plugin.py       # Main inbox/outbox bridge (policy, HMAC, logging, resilience)
├── paxect_core.py              # PAXECT Core (deterministic container engine)
└── demos/                      # Enterprise demos 1–6
    ├── demo_1_local_basic.py
    ├── demo_2_policy_hmac.py
    ├── demo_3_multi_node.py
    ├── demo_4_observability.py
    ├── demo_5_ci_cd_pipeline.py
    └── demo_6_fail_and_recover.py
```

---

## ⚙️ Installation

**Requirements:** Python ≥ 3.8 (Core additionally needs `zstandard`, `psutil`)

```bash
# Virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Dependencies for PAXECT Core
python -m pip install --upgrade pip
pip install zstandard psutil
```

---

## ✅ Verification

**Health check**

```bash
python3 paxect_link_plugin.py
```

Expected: startup banner, path summary, and “Watching…” line (Ctrl + C to stop).

**Deterministic relay check**

```bash
export PAXECT_CORE="python $(pwd)/paxect_core.py"
export PAXECT_LINK_INBOX=/tmp/pax_in
export PAXECT_LINK_OUTBOX=/tmp/pax_out
export PAXECT_LINK_POLICY=/tmp/pax_policy.json
mkdir -p "$PAXECT_LINK_INBOX" "$PAXECT_LINK_OUTBOX"

python3 - <<'PY'
import json, os, socket
p=os.environ["PAXECT_LINK_POLICY"]
d={"version":"1.2.0","trusted_nodes":[socket.gethostname(),"localhost"],
   "allowed_suffixes":[".bin",".txt",".json",".csv",".aead",".freq"],
   "max_file_mb":256,"require_sig":False,"auto_delete":True,"log_level":"info"}
open(p,"w").write(json.dumps(d,indent=2))
PY

python3 paxect_link_plugin.py   # terminal A, keep running
# terminal B:
echo "hello" > /tmp/pax_in/hello.txt
# Expect: hello.freq (+ .sha256) appears; 'hello' appears in outbox
```

✅ This manual relay verification remains valid for all demos 1–6.

---

## 🧪 Testing & Coverage

The demos double as smoke tests for continuous integration.

| Demo | Purpose                                   | CI Integration                          |
| ---- | ----------------------------------------- | --------------------------------------- |
| 05   | Deterministic encode/decode + JUnit XML   | GitHub Actions, Jenkins, GitLab         |
| 06   | Fault-injection + automatic self-recovery | Stability regression / resilience tests |

**Example run:**

```bash
python3 demos/demo_5_ci_cd_pipeline.py
python3 demos/demo_6_fail_and_recover.py
```

---

## 📦 Integration in CI/CD (GitHub Actions Example)

```yaml
name: PAXECT Link — CI/CD Smoke & Resilience Suite

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  paxect-link-suite:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Create venv + install dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate
          python -m pip install --upgrade pip
          pip install zstandard psutil

      - name: Run Demo 5 (CI/CD Smoke)
        run: |
          source .venv/bin/activate
          python demos/demo_5_ci_cd_pipeline.py

      - name: Upload JUnit results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: paxect-junit
          path: /tmp/paxect_demo5/junit_smoke.xml

      - name: Run Demo 6 (Fail & Self-Recover)
        run: |
          source .venv/bin/activate
          python demos/demo_6_fail_and_recover.py
```

**Explanation**

| Step   | Purpose                                                                    |
| ------ | -------------------------------------------------------------------------- |
| Demo 5 | Deterministic CI/CD smoke test — verifies Core + Link and emits JUnit XML. |
| Upload | Publishes `junit_smoke.xml` as CI artifact.                                |
| Demo 6 | Fault-injection + auto-recovery check; ensures resilience under failure.   |

✅ Both steps exit 0 when healthy, allowing green CI pipelines.

---

## 🧭 Bridge Diagram

```text
Producer(s)            PAXECT Link                 Consumer(s)
  write → INBOX   ──>  encode (.freq)  ──>  decode  ──> OUTBOX → read
                     (CRC32 + SHA-256)     (verify)
```

---

## 📈 Verification Summary

| Environment           | Result                                      |
| --------------------- | ------------------------------------------- |
| Ubuntu 24.04 (x86_64) | ✅ All six demos completed deterministically |
| macOS 14 Sonoma       | ✅ Identical hashes across runs              |
| Windows 11            | ✅ Inbox/outbox relay + recovery verified    |

---

## 🧩 Environment Variables (Link)

| Variable                  | Purpose                            | Example                         |
| ------------------------- | ---------------------------------- | ------------------------------- |
| `PAXECT_LINK_INBOX`       | Directory to watch for inputs      | `/tmp/paxect_demo*/inbox`       |
| `PAXECT_LINK_OUTBOX`      | Directory to write decoded outputs | `/tmp/paxect_demo*/outbox`      |
| `PAXECT_LINK_POLICY`      | JSON policy file                   | `/tmp/paxect_demo*/policy.json` |
| `PAXECT_LINK_LOG`         | JSONL log file                     | `/tmp/paxect_demo*/log.jsonl`   |
| `PAXECT_LINK_MANIFEST`    | Self manifest path                 | `/tmp/.../link_manifest.json`   |
| `PAXECT_LINK_HMAC_KEY`    | HMAC key for signed manifests      | `supersecret-demo-hmac-key`     |
| `PAXECT_LINK_LOCK`        | Lock file path (per node)          | `/tmp/.../.paxect_link.lock`    |
| `PAXECT_CORE`             | How to invoke Core                 | `python paxect_core.py`         |
| `PAXECT_LINK_POLL_SEC`    | Polling interval                   | `2.0`                           |
| `PAXECT_LINK_BACKOFF_SEC` | Backoff after failure              | `2.0`                           |

---

## 🔐 Policy Tips

* Add your **hostname** (e.g., `PAXECT-Interface`) to `trusted_nodes`.
* Include `.freq` in `allowed_suffixes`.
* Set `require_sig: true` to enforce HMAC verification.
* Unsigned or invalid peer manifests will be rejected automatically.

---

## ⚠️ Troubleshooting

* **Policy blocks (untrusted_node)** → add your hostname to `trusted_nodes`.
* **Two Link instances, one exits** → use unique lock files per node.
* **PEP 668 errors on Ubuntu** → use a virtual environment.
* **No output in outbox** → check JSONL log for `policy_block`, `encode_error`, `decode_error`.
* **Corrupted input (Demo 6)** → see `checksum_mismatch` → then `decode` in log for recovery proof.

---

## 🪪 License

All demo scripts and plugins are licensed under **Apache-2.0** (see file headers).

---

✅ **PAXECT Link Plugin Demo Suite Complete — Enterprise-Ready (1 – 6)**







| Plugin                         | Scope                           | Highlights                                                                           | Repo                                                                                                                           |
| ------------------------------ | ------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Core**                       | Deterministic container         | `.freq` v42 · multi-channel · CRC32+SHA-256 · cross-OS · offline · no-AI             | [https://github.com/PAXECT-Interface/paxect-core.git](https://github.com/PAXECT-Interface/paxect-core.git)                             |
| **AEAD Hybrid**                | Confidentiality & integrity     | Hybrid AES-GCM/ChaCha20-Poly1305 — fast, zero-dep, cross-OS                          | [https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin](https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin) |
| **Polyglot**                   | Language bindings               | Python · Node.js · Go — identical deterministic pipeline                             | [https://github.com/PAXECT-Interface/paxect-polyglot-plugin](https://github.com/PAXECT-Interface/paxect-polyglot-plugin)       |
| **SelfTune 5-in-1**            | Runtime control & observability | No-AI guardrails, overhead caps, backpressure, jitter smoothing, lightweight metrics | [https://github.com/PAXECT-Interface/paxect-selftune-plugin](https://github.com/PAXECT-Interface/paxect-selftune-plugin)       |
| **Link (Inbox/Outbox Bridge)** | Cross-OS file exchange          | Shared-folder relay: auto-encode non-`.freq` → `.freq`, auto-decode `.freq` → files  | [https://github.com/PAXECT-Interface/paxect-link-plugin](https://github.com/PAXECT-Interface/paxect-link-plugin)               |


             

---

## Path to Paid

**PAXECT** is built to stay free and open-source at its core.

### Principles

* **Core stays free forever** — no lock-in, no hidden fees.
* **Volunteers and researchers** — full access to source, builds, and discussions.
* **Transparency** — clear dates, no surprises.
* **Fairness** — individuals stay free; organizations relying on enterprise features contribute.

### Timeline

* **Launch phase:** from the official **PAXECT product release date**, all modules — including enterprise — are free for **6 months** (global).
* **30 days before renewal:** decision to extend the free enterprise phase by another 6 months.
* **Core/baseline model:** always free with updates (definition in progress).

### Why This Matters

* **Motivation:** volunteers know their work has real impact.
* **Stability:** enterprises get predictable guarantees and funded maintenance.
* **Sustainability:** continuous evolution without compromising openness.

---

## 🤝 Community & Support

**Bug or feature request?**
[Open an Issue ›](../../issues)

**General questions or collaboration ideas?**
[Join the Discussions ›](../../discussions)

If **PAXECT Link** helped your research, deployment, or enterprise project,
please consider giving the repository a ⭐ — it helps others discover the project and supports maintenance.

---
### 🔄 Updates & Maintenance

PAXECT link Plugin follows an **open contribution model**.

- Updates, bugfixes, and improvements depend on **community and maintainer availability**.
- There is **no fixed release schedule** — stability and determinism are prioritized over speed.
- Enterprises and contributors are encouraged to submit issues or pull requests for any enhancements.
- The project owner focuses on innovation and architectural guidance rather than continuous support.

In short: updates arrive when they are ready — verified, deterministic, and tested across platforms.


## 💼 Sponsorships & Enterprise Support

**PAXECT Link** is maintained as a verified enterprise plugin.
Sponsorship enables deterministic QA across operating systems.

**Enterprise partnership options:**

* Deterministic data reproducibility compliance
* CI/CD hardening and interoperability certification
* Air-gapped deployment guidance

 **How to get involved**
- [Become a GitHub Sponsor](https://github.com/sponsors/PAXECT-Interface)  







---

## Governance & Ownership

* **Ownership:** All PAXECT products and trademarks (PAXECT™ name + logo) remain the property of the Owner.
* **License:** Source code is Apache-2.0; trademark rights are **not** granted by the code license.
* **Core decisions:** Architectural decisions and **final merges** for Core and brand-sensitive repos require **Owner approval**.
* **Contributions:** PRs welcome and reviewed by maintainers; merges follow CODEOWNERS + branch protection.
* **Naming/branding:** Do not use the PAXECT name/logo for derived projects without written permission; see `TRADEMARKS.md`.


**Contact:**
📧 [PAXECT-Team@outlook.com](mailto:PAXECT-Team@outlook.com)


✅ **Deterministic · Reproducible · Offline**

Copyright© 2025 PAXECT Systems. Deterministic interoperability for the modern enterprise.



---

<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

[![Star this repo](https://img.shields.io/badge/⭐%20Star-this%20repo-orange)](../../stargazers)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](../../actions)
[![CodeQL](https://img.shields.io/badge/CodeQL-active-lightgrey.svg)](../../actions)
[![Issues](https://img.shields.io/badge/Issues-open-blue)](../../issues)
[![Discussions](https://img.shields.io/badge/Discuss-join-blue)](../../discussions)
[![Security](https://img.shields.io/badge/Security-responsible%20disclosure-informational)](./SECURITY.md)




# PAXECT Core Complete



**Deterministic, offline-first runtime for secure, reproducible data pipelines.**  
Cross-platform, self-tuning, and fully auditable — built for real-world enterprise and open-source innovation.

---

##  Overview

**PAXECT Core Complete** is the reference implementation of the PAXECT ecosystem.  
It unifies the verified modules — Core, AEAD Hybrid, Polyglot, SelfTune, and Link —  
into one reproducible, cross-OS runtime with **10 integrated demos** and full observability.

### Core principles
- **Determinism first** — bit-identical results across systems  
- **Offline-first** — no network or telemetry unless explicitly enabled  
- **Audit-ready** — human summaries + machine-readable JSON logs  
- **Cross-platform** — Linux · macOS · Windows · FreeBSD · OpenBSD · Android · iOS  
- **Zero-dependency security** — Hybrid AES-GCM / ChaCha20-Poly1305  
- **Adaptive control** — SelfTune 5-in-1 plugin with ε-greedy logic  

---

##  Installation

### Requirements
- **Python 3.9 – 3.12** (recommended 3.11+)
- Works on **Linux**, **macOS**, **Windows**, **FreeBSD**, **OpenBSD**, **Android (Termux)**, and **iOS (Pyto)**
- No external dependencies or internet connection required

### Optional utilities
Some demos use these standard tools if available:
- `bash` (for `demo_05_link_smoke.sh`)
- `dos2unix` (for normalizing line endings)
- `jq` (for formatting JSON output)

### Install
```bash
git clone https://github.com/yourname/paxect-core-complete.git
cd paxect-core-complete
python3 -m venv venv
source venv/bin/activate      # on Windows: venv\Scripts\activate
pip install -e .
````

Verify:

```bash
python3 -c "import paxect_core; print('PAXECT Core OK')"
```

Then run any of the demos from the `demos/` folder.

---

## 📁 Repository structure

```
paxect-core-complete/
├── paxect_core.py
├── paxect_aead_hybrid_plugin.py
├── paxect_polyglot_plugin.py
├── paxect_selftune_plugin.py
├── paxect_link_plugin.py
├── demos/
│   ├── demo_01_quick_start.py
│   ├── demo_02_integration_loop.py
│   ├── demo_03_safety_throttle.py
│   ├── demo_04_metrics_health.py
│   ├── demo_05_link_smoke.sh
│   ├── demo_06_polyglot_bridge.py
│   ├── demo_07_selftune_adaptive.py
│   ├── demo_08_secure_multichannel_aead_hybrid.py
│   ├── demo_09_enterprise_all_in_one.py
│   └── demo_10_enterprise_stability_faults.py
├── test_paxect_all_in_one.py
├── ENTERPRISE_PACK_OVERVIEW.md
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── TRADEMARKS.md
├── LICENSE
└── .gitignore
```

---

##  Modules

| Module                           | Purpose                                           |
| -------------------------------- | ------------------------------------------------- |
| **paxect_core.py**               | Deterministic runtime · encode/decode · checksums |
| **paxect_aead_hybrid_plugin.py** | Hybrid AES-GCM / ChaCha20-Poly1305 encryption     |
| **paxect_polyglot_plugin.py**    | Cross-language bridge · UTF-safe transformation   |
| **paxect_selftune_plugin.py**    | Adaptive ε-greedy self-tuning · persistent state  |
| **paxect_link_plugin.py**        | Secure relay · inbox/outbox · policy validation   |

## Plugins (official)


| Plugin                         | Scope                           | Highlights                                                                           | Repo                                                                                                                           |
| ------------------------------ | ------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Core**                       | Deterministic container         | `.freq` v42 · multi-channel · CRC32+SHA-256 · cross-OS · offline · no-AI             | [https://github.com/PAXECT-Interface/paxect-core.git](https://github.com/PAXECT-Interface/paxect-core.git)                             |
| **AEAD Hybrid**                | Confidentiality & integrity     | Hybrid AES-GCM/ChaCha20-Poly1305 — fast, zero-dep, cross-OS                          | [https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin](https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin) |
| **Polyglot**                   | Language bindings               | Python · Node.js · Go — identical deterministic pipeline                             | [https://github.com/PAXECT-Interface/paxect-polyglot-plugin](https://github.com/PAXECT-Interface/paxect-polyglot-plugin)       |
| **SelfTune 5-in-1**            | Runtime control & observability | No-AI guardrails, overhead caps, backpressure, jitter smoothing, lightweight metrics | [https://github.com/PAXECT-Interface/paxect-selftune-plugin](https://github.com/PAXECT-Interface/paxect-selftune-plugin)       |
| **Link (Inbox/Outbox Bridge)** | Cross-OS file exchange          | Shared-folder relay: auto-encode non-`.freq` → `.freq`, auto-decode `.freq` → files  | [https://github.com/PAXECT-Interface/paxect-link-plugin](https://github.com/PAXECT-Interface/paxect-link-plugin) 


---

## 🧪 Demo suite (01 – 10)

Run the demos from the repository root:

```bash
python3 demos/demo_01_quick_start.py               # Basic sanity check
python3 demos/demo_02_integration_loop.py          # Adaptive loop cycles
python3 demos/demo_03_safety_throttle.py           # Short/long window throttle
python3 demos/demo_04_metrics_health.py            # Observability endpoints
bash    demos/demo_05_link_smoke.sh                # Link + policy hash check
python3 demos/demo_06_polyglot_bridge.py           # Cross-system checksum
python3 demos/demo_07_selftune_adaptive.py         # ε-adaptive learning
python3 demos/demo_08_secure_multichannel_aead_hybrid.py  # Multi-channel AEAD test
python3 demos/demo_09_enterprise_all_in_one.py     # Full integrated validation
python3 demos/demo_10_enterprise_stability_faults.py       # 2 min · 5 min · 10 min stability run
```

All demos produce structured JSON output under `/tmp/`.

---

##  Testing & Verification

Internal `pytest` and smoke-test suites are maintained locally.
End-users can rely on the integrated demo suite (01–10) for verification.
Each demo is self-contained, prints its own status, and exits cleanly.

---

## 🔒 Security & Privacy

* Default mode: **offline**, **no telemetry**
* Sensitive data handled via environment variables
* CVE hygiene follows [`SECURITY.md`](./SECURITY.md)
* AEAD Hybrid is **simulation-grade**; for production, use a verified crypto library or HSM

---

## 🏢 Enterprise Pack

See [`ENTERPRISE_PACK_OVERVIEW.md`](./ENTERPRISE_PACK_OVERVIEW.md)
for roadmap and integration notes.

Includes:

* HSM / KMS / Vault integration
* Extended policy + audit engine
* Prometheus / Grafana / Splunk / Kafka connectors
* Deployment assets (systemd, Helm, Docker)
* Compliance documentation (ISO · IEC · NIST)

---

## 🤝 Community & Governance

* **License:** Apache-2.0
* **Ownership:** All PAXECT products and trademarks remain property of the Owner
* **Contributions:** PRs welcome · feature branches only · CI must pass
* **Core merges:** Owner approval required for Core / brand-sensitive repos
* **Community conduct:** see [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)

Join as maintainer or contributor — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for roles and expectations.


### 🔄 Updates & Maintenance

PAXECT Core Complete follows an **open contribution model**.

- Updates, bugfixes, and improvements depend on **community and maintainer availability**.
- There is **no fixed release schedule** — stability and determinism are prioritized over speed.
- Enterprises and contributors are encouraged to submit issues or pull requests for any enhancements.
- The project owner focuses on innovation and architectural guidance rather than continuous support.

In short: updates arrive when they are ready — verified, deterministic, and tested across platforms.


---

## 📢 Key principles

> Determinism · Privacy · Reproducibility · Cross-Platform · Transparency

Copyright© 2025 PAXECT Systems · Licensed under Apache 2.0


---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---



<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---




<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---


## Keywords & Topics

**PAXECT Link Plugin** — deterministic inbox/outbox bridge enabling reproducible, verifiable, and secure file exchange across systems and runtimes.
Designed for zero-telemetry, offline interoperability between processes on **Linux**, **macOS**, and **Windows** — powered by **PAXECT Core v42**.

These keywords improve discoverability on GitHub and search engines:

* **Core/Bridge:** paxect, link, deterministic, reproducible, cross-platform, file-relay, inbox-outbox, watcher, interprocess, reproducibility
* **Integrity & Validation:** crc32, sha256, checksum, verification, data-integrity, deterministic-hash, fail-stop, byte-identical
* **Hardening/Runtime:** atomic-io, fsync, single-instance-lock, policy-engine, allowlist, backoff, zero-ai, offline-mode
* **Interoperability:** cross-os, cross-runtime, cli-bridge, stdin-stdout, container-format, paxect-core, deterministic-transport
* **Exchange/Pipelines:** automation, data-exchange, i/o-pipeline, reproducible-systems, batch-relay, edge-sync, universal-bridge
* **Compliance/Deployment:** audit-compliance, deterministic-computing, reproducible-results, privacy-by-default, air-gapped, enterprise, ci-cd
* **Supported Stacks:** python, nodejs, go, rust, java, csharp, swift, kotlin, php, ruby, r, julia, matlab, bash, powershell (via Core CLI)
* **Use Domains:** devops, testing, secure-handoff, data-validation, containerization, scientific-computing, device-to-device relay
* **PAXECT Ecosystem:** paxect-core, paxect-selftune, paxect-aead, paxect-link, zero-ai, deterministic-pipeline, audit-ready

## Why PAXECT Link (recap)

* Deterministic **file relay**: auto-encode non-`.freq` → `.freq`, auto-decode `.freq` → raw files
* Verifiable I/O: CRC32 per frame + SHA-256 footer via **PAXECT Core v42**
* Policy-first: trusted nodes, suffix allowlist, max file size; optional **HMAC-signed manifests**
* Crash-safe & robust: atomic `.part → fsync → rename`, **single-instance lock**
* Fully offline: zero telemetry, no sockets, reproducible behavior across OSes

## Use Cases (examples)

* Air-gapped or edge environments: deterministic file hand-off between processes/machines
* CI smoke tests for artifact integrity (encode → decode → verify)
* Secure inbox/outbox automation for ETL, batch pipelines, or device drop-folders
* Cross-runtime hand-offs using Core CLI (Python job → Link → consumer)
* Enterprise compliance workflows: auditable, checksum-verified data movement

## Integration (ecosystem overview)

* **Core:** deterministic container format (fixed header/footer, CRC32 + SHA-256)
* **AEAD Hybrid:** optional encryption layer on top of `.freq` for confidentiality
* **SelfTune:** guardrails and runtime controls (rate/backpressure/observability)
* **Link:** shared-folder automation — deterministic inbox/outbox bridge
* All components follow the same deterministic contract (CRC + SHA = verified).

## License, Community & Contact

* **License:** Apache-2.0
* **Community:** GitHub Discussions & Issues
* **Support:** enterprise@[paxect-team@outlook.com](mailto:paxect-team@outlook.com)
* **Security:** no telemetry, no cloud calls, fully offline and auditable.

---

### ✅ Launch Summary — October 2025

**Status:** Production-ready · Cross-OS verified · Deterministic encode/decode
Demos 1–5 validated on Ubuntu 24.04 LTS, Windows 11 Pro, and macOS 14 Sonoma.
File-level data integrity confirmed (CRC32 + SHA-256).
Fully compatible with **PAXECT Core v42** and related plugins (AEAD, SelfTune).
Zero-AI verified: deterministic pipelines only — no heuristics, no telemetry.

---

<!--
GitHub Topics:
paxect paxect-link deterministic reproducible reproducibility
inbox-outbox file-relay bridge automation watcher
crc32 sha256 checksum verification offline
deterministic-computing data-exchange ci-cd audit-compliance enterprise
python nodejs go rust java csharp swift kotlin php ruby r julia matlab bash powershell
paxect-core paxect-selftune paxect-aead zero-ai reproducible-systems privacy-by-default
verifiable-data secure-bridge edge-computing atomic-io single-instance-lock hmac-manifest

Keywords:
PAXECT Link, deterministic file relay, inbox outbox bridge, reproducible systems,
verifiable pipelines, CRC32, SHA256, atomic writes, offline automation,
single instance lock, policy allowlist, trusted nodes, HMAC manifests,
PAXECT Core v42, air-gapped deployments, audit-ready data movement
-->

✅ **Deterministic · Reproducible · Offline**

© 2025 PAXECT Systems. Deterministic interoperability for the modern enterprise.

