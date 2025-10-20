<p align="center">
  <img src="ChatGPT%20Image%202%20okt%202025%2C%2022_33_51.png" alt="PAXECT logo" width="200"/>
</p>

---

# 🧪 **PAXECT Link Plugin — Test and Quality Validation**

This document provides a detailed overview of the testing, coverage, and validation framework for the
**PAXECT Link Plugin** — the deterministic inbox/outbox bridge of the PAXECT ecosystem.

---

## 1. Overview

The Link Plugin is validated through a comprehensive test suite designed to ensure:

* Deterministic encode/decode behavior via **PAXECT Core**
* Strict **policy enforcement** (trusted nodes, suffix allowlist, size caps)
* Optional **HMAC-signed peer manifest** validation
* Crash-safe, single-instance operation with **per-node locks**
* Full **offline** operation with no network dependencies

Testing and coverage are performed using:

* **pytest** — structured functional and integration testing
* **coverage.py** — detailed code-path and branch coverage reports
* **zstandard**, **psutil**, **hashlib**, and **subprocess** for Core & relay checks

---

## 2. Repository Structure

```
paxect-link-plugin/
├── paxect_link_plugin.py         # Inbox/outbox bridge (policy, HMAC, logging)
├── paxect_core.py                # Deterministic container engine (encode/decode)
├── tests/                        # Automated validation suite
│   ├── test_local_relay_roundtrip.py
│   ├── test_policy_enforcement.py
│   ├── test_single_instance_lock.py
│   └── test_decode_checksum_gate.py
├── coverage_run.sh               # Script to execute full coverage tests
├── pytest.ini                    # Pytest configuration
└── README_TESTS.md               # This document
```

---

## 3. Environment Setup

```bash
# Clone repository
git clone https://github.com/<your-org>/paxect-link-plugin.git
cd paxect-link-plugin

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (Link uses stdlib; Core needs zstandard/psutil)
python3 -m pip install -U pytest coverage zstandard psutil
```

Optional (for extended experiments):

```bash
python3 -m pip install numpy
```

---

## 4. Running Tests

### Run the entire test suite:

```bash
python3 -m pytest -v
```

### Run with coverage:

```bash
python3 -m coverage run -m pytest -v
python3 -m coverage report -m
```

### Generate an HTML report:

```bash
python3 -m coverage html
# open htmlcov/index.html
```

---

## 5. Example `pytest.ini`

```ini
# pytest.ini — PAXECT Link standard configuration
[pytest]
addopts = -ra -q
testpaths = tests
python_files = test_*.py
python_functions = test_*
filterwarnings =
    ignore::DeprecationWarning
```

---

## 6. Coverage Script (`coverage_run.sh`)

```bash
#!/usr/bin/env bash
# PAXECT Link — Coverage Runner

set -e
echo "=== PAXECT Link — Coverage Test Run ==="
DATE=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
echo "Started: $DATE"
echo

rm -f .coverage || true
rm -rf htmlcov || true

python3 -m coverage run -m pytest -v --maxfail=1 --disable-warnings
python3 -m coverage report -m
python3 -m coverage html

echo
echo "HTML report generated at: htmlcov/index.html"
echo "=== Test run completed successfully ==="
```

Make it executable:

```bash
chmod +x coverage_run.sh
```

---

## 7. Test Metrics (Reference)

| Metric        | Result                         |
| ------------- | ------------------------------ |
| Tests Passed  | 100 % (all passing)            |
| Coverage      | 90–95 % (policy & relay paths) |
| Framework     | pytest + coverage.py           |
| Compatibility | Linux, macOS, Windows (WSL)    |
| Python        | 3.8 – 3.12                     |

*(Exact figures may vary by environment.)*

---

## 8. CI/CD Integration

### GitHub Actions Example

```yaml
jobs:
  link-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install pytest coverage zstandard psutil
      - name: Run Link Tests
        run: ./coverage_run.sh
      - name: Upload Coverage HTML
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: paxect-link-htmlcov
          path: htmlcov/
```

### GitLab CI Example

```yaml
link_test:
  image: python:3.12
  script:
    - python -m pip install --upgrade pip
    - pip install pytest coverage zstandard psutil
    - ./coverage_run.sh
  artifacts:
    when: always
    paths:
      - htmlcov/
```

---

## 9. Quality Principles

* **Reproducibility:** Bit-identical results for encode/decode across OSes
* **Integrity:** CRC32 per frame + SHA-256 footer check via PAXECT Core
* **Isolation:** No network or telemetry; deterministic, local-only behavior
* **Transparency:** JSONL logs with levels and rotation; inspectable events
* **Stability:** Single-instance lock; per-node locks in multi-node scenarios
* **Policy First:** Trusted nodes + suffix allowlist + max size caps
* **Trustable Peers:** Optional HMAC-signed manifests (`require_sig: true`)

---

## 10. License

All test utilities and scripts are released under the same license as the plugin:
**Apache 2.0 License** — © 2025 PAXECT Systems. All rights reserved.
