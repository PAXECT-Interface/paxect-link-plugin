<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---

[![Star this repo](https://img.shields.io/badge/⭐%20Star-this%20repo-orange)](../../stargazers)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](../../actions)
[![CodeQL](https://img.shields.io/badge/CodeQL-active-lightgrey.svg)](../../actions)
[![Issues](https://img.shields.io/badge/Issues-open-blue)](../../issues)
[![Discussions](https://img.shields.io/badge/Discuss-join-blue)](../../discussions)
[![Security](https://img.shields.io/badge/Security-responsible%20disclosure-informational)](./SECURITY.md)

---

# 🔗 **PAXECT Link — Deterministic Inbox/Outbox Bridge**

Secure, deterministic file relay across processes, runtimes, and operating systems — fully **offline**.
The **PAXECT Link Plugin** provides a reproducible, verifiable bridge by auto-encoding non-`.freq` files **to** `.freq` and auto-decoding `.freq` containers **to** raw files, powered by **PAXECT Core**.

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

| Demo | Script                     | Description                                      | Status |
| ---- | -------------------------- | ------------------------------------------------ | ------ |
| 01   | `demo_1_local_basic.py`    | Local encode→decode sanity check                 | ✅      |
| 02   | `demo_2_policy_hmac.py`    | Policy with HMAC: accept signed, reject unsigned | ✅      |
| 03   | `demo_3_multi_node.py`     | Two Link nodes, per-node lock, both decode       | ✅      |
| 04   | `demo_4_observability.py`  | JSONL logs → simple metrics summary              | ✅      |
| 05   | `demo_5_ci_cd_pipeline.py` | CI smoke; emits JUnit XML                        | ✅      |

Run all demos one by one:

```bash
python3 demos/demo_1_local_basic.py
python3 demos/demo_2_policy_hmac.py
python3 demos/demo_3_multi_node.py
python3 demos/demo_4_observability.py
python3 demos/demo_5_ci_cd_pipeline.py
```

---

## 🧩 Architecture Overview

```text
paxect-link-plugin/
├── paxect_link_plugin.py       # Main inbox/outbox bridge (policy, HMAC, logging)
├── paxect_core.py              # PAXECT Core (deterministic container engine)
└── demos/                      # Enterprise demos 1–5
    ├── demo_1_local_basic.py
    ├── demo_2_policy_hmac.py
    ├── demo_3_multi_node.py
    ├── demo_4_observability.py
    └── demo_5_ci_cd_pipeline.py
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

Health:

```bash
python3 paxect_link_plugin.py
```

Expected: startup banner, paths, and a “Watching…” line (Ctrl+C to stop).

Deterministic relay check:

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

---

## 🧪 Testing & Coverage

The demos double as smoke tests. For CI integration, use **Demo 5**:

```bash
python3 demos/demo_5_ci_cd_pipeline.py ; echo "exit=$?"
# JUnit XML: /tmp/paxect_demo5/junit_smoke.xml
```

---

## 📦 Integration in CI/CD

**GitHub Actions Example**

```yaml
jobs:
  paxect-link-smoke:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Venv + deps
        run: |
          python -m venv .venv
          source .venv/bin/activate
          python -m pip install --upgrade pip
          pip install zstandard psutil
      - name: Demo 5 (JUnit)
        run: |
          source .venv/bin/activate
          python demos/demo_5_ci_cd_pipeline.py
      - name: Upload JUnit
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: paxect-junit
          path: /tmp/paxect_demo5/junit_smoke.xml
```

---

## 🧭 Bridge Diagram

```text
Producer(s)            PAXECT Link                 Consumer(s)
  write → INBOX   ──>  encode (.freq)  ──>  decode  ──> OUTBOX → read
                     (CRC32 + SHA-256)     (verify)
```

---

## 📈 Verification Summary

| Environment           | Result                                  |
| --------------------- | --------------------------------------- |
| Ubuntu 24.04 (x86_64) | ✅ All demos completed deterministically |
| macOS 14 Sonoma       | ✅ Identical hashes across runs          |
| Windows 11            | ✅ Inbox/outbox relay verified           |

---

| Plugin                         | Scope                       | Highlights                                                                                  | Repo                                                                                                                           |
| ------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **AEAD Hybrid**                | Confidentiality & integrity |    “Hybrid AES-GCM/ChaCha20-Poly1305 — fast, zero-dep, cross-OS.”                      | [https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin](https://github.com/PAXECT-Interface/paxect-aead-hybrid-plugin) |
| **Polyglot**                   | Language bindings           | Python, Node.js, Go; identical deterministic pipeline across runtimes                       | [https://github.com/PAXECT-Interface/paxect-polyglot-plugin](https://github.com/PAXECT-Interface/paxect-polyglot-plugin)       |
| **SelfTune 5-in-1**            | Performance & observability | No-AI autotune: guardrails, overhead control, backpressure, jitter smoothing, observability | [https://github.com/PAXECT-Interface/paxect-selftune-plugin](https://github.com/PAXECT-Interface/paxect-selftune-plugin)       |
| **Link (Inbox/Outbox Bridge)** | Cross-OS file exchange      | Shared-folder bridge; auto-encode non-`.freq` → `.freq`, auto-decode `.freq` → files        | [https://github.com/PAXECT-Interface/paxect-link-plugin](https://github.com/PAXECT-Interface/paxect-link-plugin)               |

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

## 💼 Sponsorships & Enterprise Support

**PAXECT Link** is maintained as a verified enterprise plugin.
Sponsorship enables deterministic QA across operating systems.

**Enterprise partnership options:**

* Deterministic data reproducibility compliance
* CI/CD hardening and interoperability certification
* Air-gapped deployment guidance

 **How to get involved**
- [Become a GitHub Sponsor](https://github.com/sponsors/PAXECT-Interface)  

**Contact:**
📧 enterprise@[PAXECT-Team@outlook.com](mailto:PAXECT-Team@outlook.com)

---

## 🪪 License

---

## Governance & Ownership

* **Ownership:** All PAXECT products and trademarks (PAXECT™ name + logo) remain the property of the Owner.
* **License:** Source code is Apache-2.0; trademark rights are **not** granted by the code license.
* **Core decisions:** Architectural decisions and **final merges** for Core and brand-sensitive repos require **Owner approval**.
* **Contributions:** PRs welcome and reviewed by maintainers; merges follow CODEOWNERS + branch protection.
* **Naming/branding:** Do not use the PAXECT name/logo for derived projects without written permission; see `TRADEMARKS.md`.


---


✅ **Deterministic · Reproducible · Offline**

© 2025 PAXECT Systems. Deterministic interoperability for the modern enterprise.





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

