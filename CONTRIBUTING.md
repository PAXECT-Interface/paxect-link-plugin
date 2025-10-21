<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>



# **Contributing Guidelines**

Thank you for your interest in contributing to the **PAXECT Link Plugin**.

---

## Overview

This repository is part of the **PAXECT Interface Ecosystem**.
All contributions must remain:

* **Deterministic:** no random timing, unpredictable I/O, or race conditions
* **Cross-platform:** must operate identically on Linux, macOS, and Windows
* **Secure:** aligned with PAXECT Core’s offline-first and privacy-by-design principles
* **Dependency-free:** no cloud APIs, telemetry, or AI/ML frameworks
* **Consistent:** inbox/outbox relay behavior must be reproducible and byte-identical across runs

Each change must preserve **message integrity**, **transport reproducibility**,
and **cross-OS deterministic link stability** under all supported environments.

---

## Development Setup

### 1. Fork the repository

Create your own fork to contribute safely.

### 2. Clone your fork locally

```bash
git clone https://github.com/<your-username>/paxect-link-plugin.git
cd paxect-link-plugin
```

### 3. (Optional) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 5. Run a basic verification

```bash
python3 demos/demo_1_local_basic.py
```

---

## Testing Standards

* Use **pytest** for all new tests (`tests/` directory).
* Keep tests **deterministic and cross-platform safe**.
* Validate both **inbox/outbox relay** and **streamed I/O** modes.
* Avoid hardcoded paths — always use `tempfile` for test data.
* Ensure **relay consistency** and **link health endpoints** (`/ping`, `/ready`, `/metrics`) all respond correctly.

Example:

```bash
python3 -m pytest -v
```

---

## Pull Requests

* Use branch names like:
  `feature/<short-description>` or `fix/<issue-id>`

* Add a clear description and link related issues.

* Before submitting, verify that **all 6 demo scripts** still execute successfully:


```bash
python3 demos/01_auto_relay_simulation.py
python3 demos/02_live_relay_monitor.py
python3 demos/03_multi_node_link.py
python3 demos/04_overhead_guard_link.py
python3 demos/05_ci_cd_pipeline_smoke.py
python3 demos/06_fail_and_recover.py

  ```

* Each demo must produce **consistent deterministic output** across Linux, macOS, and Windows.

* All relay endpoints must respond correctly:
  `/ping`, `/ready`, `/metrics`, `/last`

* Code must pass linting and style checks:

  ```bash
  flake8 && black --check .
  ```

* Commit messages should follow the conventional format:

  ```
  feat: add multi-node relay consistency test
  fix: correct HMAC policy mismatch on Windows
  docs: update observability demo instructions
  ```

---

## Security and Compliance

* No third-party telemetry, analytics, or external networking.
* No AI-generated or probabilistic link behavior.
* Each PR is automatically checked for **deterministic compliance**
  and **relay integrity safety**.
* Secrets, tokens, or credentials **must never** appear in source code.

For confidential security concerns, report privately to:
📧 **[paxect-team@outlook.com](mailto:paxect-team@outlook.com)**

---

## Communication

* **Issues:** Bug reports, feature requests, reproducibility feedback
* **Discussions:** Technical proposals or link protocol architecture
* **Security:** Coordinated disclosure via private email

---

## License

All contributions fall under the **Apache 2.0 License**
and are subject to **PAXECT’s deterministic, audit-compliant development policies**.

---

