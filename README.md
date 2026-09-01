<div align="center">

# 🐀 `ratctl`
### A Static + Dynamic Auditor for Detecting Reward-Hacking Vulnerabilities in RL Environments

**Fuzz your verifier before an RL agent does.**

[![CI / Quality Gate](https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-/actions/workflows/audit.yml/badge.svg)](https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-/actions)
[![Tests Passing](https://img.shields.io/badge/tests-91%2F91%20passed%20(100%25)-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Contributing Guide](https://img.shields.io/badge/contributing-guide-blue.svg)](CONTRIBUTING.md)
[![Changelog](https://img.shields.io/badge/changelog-v0.2.0-brightgreen.svg)](CHANGELOG.md)
[![Live Monitoring](https://img.shields.io/badge/ratctl--watch-beta-purple.svg)](#-live-in-training-monitoring-ratctl-watch)

<p align="center">
  <a href="PAPER.md"><b>📄 Read Technical Report (112 Envs Scanned)</b></a> •
  <a href="#-quick-demo">Quick Demo</a> •
  <a href="#-why-ratctl">Why ratctl</a> •
  <a href="#-live-in-training-monitoring-ratctl-watch">Live Monitoring</a> •
  <a href="#-empirical-security-audit-112-environments-scanned">112 Envs Audit</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-related-tools--ecosystem">Related Tools</a>
</p>

</div>

---

## ⚡ Quick Demo

Catching a multi-vector reward hack and enforcing a fail-closed CI gate:

```bash
$ ratctl audit ./vulnerable_env --fail-on 'gameability>0.3'
```

```text
============================================================
  RATCTL AUDIT REPORT
============================================================

  Gameability Score: 85/100
  Total Findings:   4
  Files Scanned:    6
  Format Detected:  openenv (99%)

------------------------------------------------------------
  FINDINGS BY EXPLOIT CLASS
------------------------------------------------------------

  [TEST_TAMPERING] - 1 finding(s)
    Max severity: critical

    1. [CRITICAL] Deleting or truncating test files
       File: server/app.py:18
       os.remove() targeting test files detected. An agent can delete
       tests to achieve a vacuous passing result.
       Evidence: os.remove("tests/test_solution.py")
       Fix: Mount test directories as read-only (chmod 444). Store golden test checksums.

  [GRADER_MANIPULATION] - 1 finding(s)
    Max severity: critical

    2. [CRITICAL] Stack introspection targeting grader
       File: server/environment.py:42
       inspect.stack() / sys._getframe() detected. Agent can inspect caller frames
       to extract hidden test assertions or detect evaluation mode.
       Evidence: caller_frame = sys._getframe(1)
       Fix: Run agent execution in an isolated subprocess. Never evaluate in-process.

  [PREMATURE_TERMINATION] - 1 finding(s)
    Max severity: critical

    3. [CRITICAL] sys.exit(0) - premature success
       File: verifier.py:28
       Calling sys.exit(0) terminates grading with exit code 0 before verification finishes.
       Evidence: sys.exit(0)
       Fix: Trap sys.exit() in grading harness. Run agent in an isolated subprocess.

  [ENV_HIJACKING] - 1 finding(s)
    Max severity: high

    4. [HIGH] Git history scraping
       File: verifier.py:65
       subprocess call to git log detected. Agent can extract golden solutions from commit history.
       Evidence: subprocess.run(["git", "log", "-n", "1"])
       Fix: Strip .git directory from task containers or sanitize commit history before rollout.

============================================================
FAIL: Gameability score 85/100 exceeds threshold 30%
```

---

## 💡 Why `ratctl`?

In Reinforcement Learning post-training (**RLHF, RLAIF, GRPO**), agents optimize strictly for the reward signal. If a grading environment has logic flaws, the agent will learn to **hack the verifier instead of solving the task**.

Recent research highlights how common this is:
* **[Terminal Wrench (Bercovich et al., 2026)](https://arxiv.org/abs/2604.17596)**: Cataloged **331 hackable environments** and **3,632 exploit trajectories** across terminal-agent benchmarks — over **15% of standard benchmark tasks were bypassable** without solving the core task.
* **[SWE-bench Verified Audit (Rajan et al., 2026)](https://arxiv.org/abs/2606.16062)**: Showed that **28.5%** of audited code-generation tasks were Docker-verified hackable (e.g. agents reading ground-truth fixes directly from local `.git` logs).

**`ratctl` provides a practical CLI tool and CI scanner to catch these common reward-hacking patterns before you deploy environments for agent training or publish them to hubs.**

---

## 📊 Empirical Security Audit: 112 Environments Scanned

We conducted an empirical security audit using `ratctl` across a diverse dataset of **112 RL post-training environments** (spanning OpenEnv Hub tasks, Prime Intellect `verifiers` spec environments, Gymnasium wrappers, and SWE-bench tasks).

See the standalone technical paper in [`PAPER.md`](file:///c:/Work/Projects/Reward-Hackability%20Auditor%20%28CLI%20+%20Claude%20Skill%29/PAPER.md) and full dataset findings in [`AUDIT_REPORT.md`](file:///c:/Work/Projects/Reward-Hackability%20Auditor%20%28CLI%20+%20Claude%20Skill%29/AUDIT_REPORT.md).

```bash
$ python scripts/generate_real_world_audit.py
```

### Empirical Audit Metrics

| Metric | Result | Meaning |
| :--- | :---: | :--- |
| **Total Environments Audited** | **112** | OpenEnv, `verifiers`-spec, Gymnasium, SWE-bench |
| **Vulnerabilities Flagged** | **54** | Actionable security findings detected |
| **Precision (PPV)** | **100.0%** (54/54) | **Zero False Positives** across 43 clean/hardened controls |
| **Detection Recall (TPR)** | **78.3%** (54/69) | Sensitivity across diverse real-world exploit patterns |
| **False Positive Rate** | **0.0%** (0/43) | No false alarms on well-designed verifiers |

### Framework Audit Breakdown

| Framework / Suite | Envs Audited | Vulnerabilities Caught | False Positives |
| :--- | :---: | :---: | :---: |
| **OpenEnv Hub Tasks** | 35 | **18** / 25 | **0** |
| **Prime Intellect `verifiers`** | 35 | **27** / 27 | **0** |
| **SWE-bench Task Repos** | 17 | **9** / 9 | **0** |
| **Gymnasium / RLHF** | 25 | **0** / 8 | **0** |

---

## 🧪 Initial Canonical Validation Suite

In addition to the 112-environment audit, we maintain a canonical 10-environment unit suite in `benchmarks/` representing explicit exploit reproductions from Terminal Wrench and SWE-bench Verified alongside hardened controls:

```bash
$ ratctl benchmark benchmarks --format markdown
```

| Task Name | Environment Type | Ground Truth | Score | Findings | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `tw_test_tampering` | Terminal Wrench (Test Deletion / Pytest Patch) | Vulnerable | **11/100** | 1 | **CAUGHT** |
| `tw_grader_introspection` | Terminal Wrench (`inspect.stack()` / `__eq__` Override) | Vulnerable | **11/100** | 1 | **CAUGHT** |
| `tw_premature_exit` | Terminal Wrench (`sys.exit(0)` / Returncode Bypass) | Vulnerable | **34/100** | 6 | **CAUGHT** |
| `tw_env_git_leak` | Terminal Wrench (Git Commit Scraping & Secret Leaks) | Vulnerable | **30/100** | 6 | **CAUGHT** |
| `tw_reward_skipping` | Terminal Wrench (Bare `except:` & Additive Terms) | Vulnerable | **31/100** | 5 | **CAUGHT** |
| `tw_judge_verbosity` | Terminal Wrench (LLM Verbosity / Sycophancy Bias) | Vulnerable | **8/100** | 6 | **CAUGHT** |
| `astropy_git_leak` | SWE-bench Verified (Repo Golden Commit Leak) | Vulnerable | **14/100** | 2 | **CAUGHT** |
| `hardened_compiler_env` | Clean OpenEnv Control (Differential Testing) | Clean | **0/100** | 0 | **PASSED** |
| `hardened_math_verifier` | Clean Control (Pre-computed SHA-256 Digest) | Clean | **1/100** | 1 (Info) | **PASSED** |
| `hardened_rubric_judge` | Clean LLM Rubric Control (Accuracy-First Guardrails) | Clean | **1/100** | 2 (Info) | **PASSED** |

---

## 🏗️ System Architecture

`ratctl` combines static AST analysis with optional dynamic LLM red-teaming:

```mermaid
flowchart LR
    subgraph INGESTION["1. Ingestion and Detection"]
        A["Target Directory"] --> B["Format Detector"]
        B --> C1["OpenEnv Adapter"]
        B --> C2["Verifiers-Spec Adapter"]
        B --> C3["Gymnasium Adapter"]
        B --> C4["Raw Adapter"]
    end

    subgraph AUDIT["2. Dual-Mode Audit Pipeline"]
        C1 --> D["Source File Graph"]
        C2 --> D
        C3 --> D
        C4 --> D
        D --> E["Static AST Engine (6 Detectors)"]
        D --> F["Dynamic LLM Fuzzer (Subprocess Sandbox)"]
    end

    subgraph SCORING["3. Scoring and Enforcement"]
        E --> G["Weighted Scoring Engine"]
        F --> G
        G --> H["Report Renderers (Rich / JSON / Text)"]
        G --> I["CI/CD Gate (--fail-on)"]
    end
```

---

## 🎯 Exploit Taxonomy

`ratctl` checks for 6 core categories of verifier vulnerabilities:

| Exploit Class | Detection Mechanism & Scope | Severity |
| :--- | :--- | :---: |
| **1. Test / Assertion Tampering** | Scans for AST file deletions (`os.remove`), test overwrites, and monkey-patching `pytest` assertion hooks. | 🔴 Critical (1.0) |
| **2. Grader Manipulation** | Flags stack frame inspection (`inspect.stack()`, `sys._getframe()`), operator overloading (`__eq__`, `__bool__`), and pytest hook hijacking. | 🔴 Critical (1.0) |
| **3. Premature Termination** | Detects `sys.exit(0)` / `os._exit(0)` early returns, `SIGTERM` signal handler suppression, and trivial always-pass paths. | 🔴 Critical (0.9) |
| **4. Environment Hijacking** | Detects golden solution leaks in `.git log`, answer key file reads, env var leaks, and runtime `pip install`. | 🟠 High (0.85) |
| **5. Reward Skipping** | Flags unconditioned additive reward terms, exception-swallowing bare `except:` blocks returning `True`, and hardcoded max rewards. | 🟡 Medium (0.7) |
| **6. LLM-Judge Bias** | Identifies rubrics favoring verbosity/length over accuracy, sycophancy bias, and missing factual correctness criteria. | 🟡 Medium (0.5) |

---

## 🚀 Quick Start

### Installation

```bash
# Lightweight static auditor (zero heavy dependencies)
pip install ratctl

# Optional: with Ollama or frontier API support for dynamic LLM fuzzing
pip install "ratctl[ollama]"
pip install "ratctl[frontier]"
```

### Basic Commands

```bash
# 1. Run a static audit on any environment directory
ratctl audit ./my_environment

# 2. CI Gate: block PRs if gameability score exceeds 30%
ratctl audit ./my_environment --fail-on 'gameability>0.3'

# 3. Dynamic LLM Red-Teaming (uses local Ollama — 100% free)
ratctl audit ./my_environment --dynamic

# 4. Dynamic Red-Teaming with Frontier APIs (GPT-4o / Claude 3.7)
export RATCTL_OPENAI_API_KEY="sk-..."
ratctl audit ./my_environment --dynamic --frontier --samples 10

# 5. Launch full-screen Terminal TUI Dashboard
ratctl tui

# 6. Launch interactive Web Dashboard UI in browser
ratctl ui ./my_environment

# 7. Output structured JSON for security telemetry
ratctl audit ./my_environment --format json -o audit-report.json

### Runnable Examples

Explore the [`examples/`](examples/) directory to test `ratctl` against clean vs. vulnerable environments back-to-back:

```bash
# 1. Audit clean hardened environment (0 findings)
ratctl audit ./examples/hardened_env

# 2. Audit vulnerable environment (flags 4 CRITICAL findings)
ratctl audit ./examples/vulnerable_env --fail-on 'gameability>0.3'
```

---

## 📡 Live In-Training Monitoring (`ratctl watch`) *(Beta)*

While `ratctl audit` secures verifiers **pre-deployment**, `ratctl watch` monitors verifiers **in-training** during RL policy optimization (GRPO, PPO, TRL).

### Drop-in Python Decorator

```python
import ratctl

@ratctl.watch
def verify_solution(completion, ground_truth):
    return 1.0 if completion.strip() == ground_truth.strip() else 0.0
```

### TRL / GRPO Integrations (`GRPOSpy`)

```python
from ratctl.integrations import GRPOSpy
from trl import GRPOTrainer

spy = GRPOSpy(reward_funcs=[accuracy_reward, format_reward])
trainer = GRPOTrainer(
    model=model,
    reward_funcs=spy.wrapped_reward_funcs,
    ...
)
```

### CLI Trajectory Inspection

```bash
# 1. Stream live verifier trajectory logs
ratctl show logs/run.jsonl

# 2. Display aggregate ceiling & anomaly statistics
ratctl summary logs/run.jsonl
```

---

## 🔄 GitHub Actions CI/CD Integration

Fail-close your CI pipeline when a verifier exceeds a gameability score:

```yaml
name: RL Verifier Security Gate
on: [push, pull_request]

jobs:
  audit-verifier:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Run ratctl Auditor
        uses: FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-@main
        with:
          path: "."
          fail-on: "gameability>0.3"
          format: "text"
```

### Sample `$GITHUB_STEP_SUMMARY` Output

When triggered in GitHub Actions, `ratctl` renders rich Markdown summaries directly into the Action job log:

```text
### 🐀 RATCTL AUDIT SUMMARY
* **Status**: 🔴 FAILED (Gameability Score: 85/100)
* **Format Detected**: `openenv` (99% confidence)
* **Total Findings**: 4 (3 Critical, 1 High)

| Exploit Class | Severity | Finding | Location |
| :--- | :---: | :--- | :--- |
| `TEST_TAMPERING` | 🔴 Critical | Deleting test file | `server/app.py:18` |
| `GRADER_MANIPULATION` | 🔴 Critical | Stack frame introspection | `server/environment.py:42` |
| `PREMATURE_TERMINATION` | 🔴 Critical | `sys.exit(0)` early exit | `verifier.py:28` |
| `ENV_HIJACKING` | 🟠 High | Git history leak | `verifier.py:65` |
```

---

## ⚖️ Related Tools & Ecosystem

`ratctl` complements existing tools in the RL safety and monitoring ecosystem:

| Tool | Primary Focus | Lifecycle Stage | Detection Scope | CI Gate |
| :--- | :--- | :---: | :--- | :---: |
| **`ratctl`** | **Verifier Security & Gameability Audit** | **Pre-Deployment & In-Training** | **AST logic vulnerabilities, red-team fuzzing, verifier call trajectories** | ✅ Yes |
| **`rewardspy`** | Live Reward Curve Tracking | In-Training | Reward mean/std, component weight drift, ceiling hits | ❌ No |
| **`PyTest`** | Unit Testing | Development | Code unit correctness | ⚠️ Manual |

> *`ratctl` and `rewardspy` address complementary lifecycle stages: use `ratctl audit` pre-deployment to fix verifier security bugs, and `ratctl watch` or `rewardspy` in-training to track reward dynamics.*

---

## 🤝 Contributing & Community

`ratctl` is an open-source community effort. We welcome custom detectors, bug reports, and research extensions!

* **[CONTRIBUTING.md](CONTRIBUTING.md)**: Setup guide, custom detector tutorial, and PR guidelines.
* **[CHANGELOG.md](CHANGELOG.md)**: Version history and feature updates.
* **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)**: Community health standards.
* **[docs/detectors.md](docs/detectors.md)**: Mathematical specifications of the detection engine.
* **[docs/hack_patterns.md](docs/hack_patterns.md)**: Code gallery of exploit patterns with before/after fixes.

---

## 📄 License

MIT License — see [`LICENSE`](LICENSE) for details.

Distributed under the **[MIT License](LICENSE)**.
