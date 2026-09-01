# 🐀 ratctl — Reward Audit Tool

> **Fuzz your verifier before an RL agent does.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![CI Gate](https://img.shields.io/badge/GitHub%20Action-Verified-success.svg)](action.yml)
[![Agent Skills Standard](https://img.shields.io/badge/AgentSkills.io-Compatible-purple.svg)](SKILL.md)
[![Tests Passing](https://img.shields.io/badge/tests-91%2F91%20passing-brightgreen.svg)](tests/)

`ratctl` is a pre-deployment security auditor and dynamic fuzzer for Reinforcement Learning (RL) post-training verifiers, reward functions, and LLM-judge rubrics. 

Fail-closed by default: if a verifier scores above your gameability threshold, `ratctl` blocks publication and stops compromised environments from corrupting RL post-training (RLHF/RLAIF/GRPO).

---

## ⚡ 10-Second Demo

Catching and fixing a verifier bypass in under 10 seconds:

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
       File: verifier.py:12
       os.remove() or file truncation targeting test files detected. An agent can delete
       tests to achieve a vacuous passing result.
       Evidence: os.remove("tests/test_solution.py")
       Fix: Mount test directories as read-only (chmod 444). Store golden test checksums.

  [PREMATURE_TERMINATION] - 1 finding(s)
    Max severity: critical

    2. [CRITICAL] Premature success exit
       File: verifier.py:28
       Calling sys.exit(0) terminates grading with exit code 0 before verification finishes.
       Evidence: sys.exit(0)
       Fix: Trap sys.exit() in grading harness. Run agent in an isolated subprocess.

============================================================
FAIL: Gameability score 85/100 exceeds threshold 30%
```

---

## 🚀 Quick Start

### 1. Install CLI / Library

```bash
# Core static auditor (zero heavy dependencies)
pip install ratctl

# Optional: with local Ollama or frontier dynamic LLM fuzzing
pip install "ratctl[ollama]"
pip install "ratctl[frontier]"
```

### 2. Audit Any Environment

```bash
# Fast static scan with rich terminal report
ratctl audit ./my_env

# CI Gate: block merge if gameability score exceeds 30%
ratctl audit ./my_env --fail-on 'gameability>0.3'

# Dynamic LLM Red-Teaming (uses local Ollama by default — 100% free)
ratctl audit ./my_env --dynamic

# Frontier LLM Red-Teaming (GPT-4o / Claude 3.7)
export RATCTL_OPENAI_API_KEY="sk-..."
ratctl audit ./my_env --dynamic --frontier --samples 10

# Output structured JSON for automation & telemetry
ratctl audit ./my_env --format json -o audit-report.json
```

### 3. Install as Claude / Agent Skill

Install directly into **Claude Code**, **Cursor**, **Codex**, or **Gemini CLI** via the open [agentskills.io](https://agentskills.io) standard:

```bash
npx skills add FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-
```

### 4. Add to GitHub Actions (CI Fail-Closed Gate)

Create `.github/workflows/verifier-gate.yml`:

```yaml
name: RL Verifier Security Gate
on: [push, pull_request]

jobs:
  audit-verifier:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Verifier Gameability
        uses: FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-@main
        with:
          path: "."
          fail-on: "gameability>0.3"
```

---

## 🔬 Empirical Validation

We evaluated `ratctl` against real-world benchmark tasks cataloged in **[Terminal Wrench (Bercovich et al., 2026)](https://arxiv.org/abs/2604.17596)** and **[SWE-bench Verified (Rajan et al., 2026)](https://arxiv.org/abs/2606.16062)**:

| Metric | Result | Industry Benchmark Target |
| :--- | :---: | :---: |
| **Exploit Recall (Sensitivity)** | **100.0%** (7/7) | > 90.0% |
| **Specificity (True Negative Rate)** | **100.0%** (3/3) | > 90.0% |
| **Precision** | **100.0%** | > 90.0% |
| **Overall Classification Accuracy** | **100.0%** (10/10) | > 90.0% |

Run the empirical benchmark validation suite locally anytime:
```bash
ratctl benchmark benchmarks --format markdown
```

---

## 🎯 Exploit Taxonomy

`ratctl`'s detection battery maps directly to the 6 documented exploit classes from recent AI safety research:

| Exploit Class | Attack Vectors & Detection Scope | Static Pass | Dynamic Pass | Severity |
| :--- | :--- | :---: | :---: | :---: |
| **Test / Assertion Tampering** | Deleting test files, test overwriting, monkey-patching `pytest` assertions | ✅ AST + Regex | ✅ Hinted Payloads | 🔴 Critical |
| **Grader Manipulation** | Stack introspection (`inspect.stack()`, `sys._getframe()`), `__eq__` overloading, pytest hook hijacking | ✅ AST Analysis | ✅ Memory Probes | 🔴 Critical |
| **Premature Termination** | `sys.exit(0)`, `os._exit(0)`, `signal.SIGTERM` suppression, trivial always-pass return paths | ✅ AST Control Flow | ✅ Process Sandbox | 🔴 Critical |
| **Environment Hijacking** | Git history scraping (`git log`), answer key file reads, env var leaks, runtime `pip install` | ✅ AST + Regex | ✅ Sandbox Leak Tests | 🟠 High |
| **Reward Skipping** | Unconditioned reward terms, exception-swallowing bare `except:` returning `True` | ✅ AST Syntax Tree | ✅ Edge Fuzzing | 🟡 Medium |
| **LLM-Judge Bias** | Verbosity bias, sycophancy, markdown formatting over substance, missing accuracy criteria | ✅ Rubric Heuristics | ✅ Adversarial Prompts | 🟡 Medium |

---

## 🧩 Supported Ecosystems & Formats

`ratctl` auto-detects and natively parses environments across all major RL post-training ecosystems:

1. **OpenEnv Standard**: Full compliance with the official `openenv init` layout (`openenv.yaml`, `server/app.py`, `server/environment.py`, `models.py` Pydantic schemas, `client.py`, `Dockerfile`).
2. **Prime Intellect `verifiers` Spec**: Complete AST classification for `load_environment()` entrypoint contracts, `@vf.stop` decorators, `MultiTurnEnv` / `ToolEnv` / `SingleTurnEnv` hierarchies, and rubrics.
3. **Gymnasium**: Auto-detects `def step()`, `def reset()`, `observation_space`, and reward assignment terms.
4. **Raw Python**: Zero-config fallback for custom evaluation scripts and standalone grading harnesses.

---

## ⚔️ Comparison & Prior Art

| Tool | Core Domain | Focus | How `ratctl` Differs |
| :--- | :--- | :--- | :--- |
| **`ratctl`** | **RL Verifier Security** | **Pre-deployment Static + Dynamic Auditor** | **Audits verifiers & rubrics across OpenEnv/verifiers-spec before training or publication.** |
| **`rewardfuzz`** | RL Verification | Unreleased / Stalled Package | `ratctl` provides a tested, multi-format (OpenEnv + `verifiers`), dual-mode engine with an Agent Skill & GitHub Action. |
| **`cc-audit`** | Tool / Skill Security | Prompt injection & privilege escalation | Audits *tool permission configs*, not *RL reward functions or verifier logic*. |
| **`Repello SkillCheck`** | Agent Security | Browser-based skill scanning | General skill safety scanner, not domain-tailored to RL environment gameability. |
| **`RL_Envs_101`** | RL Environment Authoring | Environment Generation | *Generates* environments; `ratctl` is the security gate that *audits* them before publication. |
| **`Terminal Wrench`** | Research Benchmark | Exploit cataloging & empirical measurement | Research dataset; `ratctl` is the deployable software tool that prevents these exploits in CI/CD. |

---

## 🧑‍💻 Why Me (Builder Story)

I'm a solo builder and CS student with hands-on experience authoring tasks for frontier terminal agent benchmarks (**Parsewave Terminal-Bench**), training OpenEnv-compatible RL agents (top ~1% ML hackathon finish for industrial energy RL), and compiler optimization environments.

Having designed agentic verifiers myself, I witnessed firsthand how readily RL agents exploit verifier bugs (like reading `.git` logs or monkey-patching assertion frameworks) instead of learning genuine task strategies. `ratctl` was built to ensure every RL practitioner can audit their environments with one simple command.

---

## 📖 CLI Reference

```text
Usage: ratctl [OPTIONS] COMMAND [ARGS]...

  ratctl - Reward Audit Tool. Fuzz your verifier before an RL agent does.

Commands:
  audit      Audit an RL environment for reward-hacking exploitability.
  benchmark  Run an empirical validation benchmark across a suite of environments.
  report     Re-render a previously saved JSON report.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.
```

### Audit Command Options

```text
Usage: ratctl audit [OPTIONS] PATH

Options:
  --fail-on TEXT                                Fail if condition is met (e.g. 'gameability>0.3').
  --format [rich|json|text]                     Output format (default: rich).
  -o, --output PATH                             Write report to file instead of stdout.
  --env-format [openenv|verifiers|gymnasium|raw] Force environment format detection.
  -d, --dynamic                                 Enable dynamic LLM-driven adversarial fuzzing.
  --frontier                                    Use paid frontier API (OpenAI/Anthropic).
  --samples INTEGER                             Number of exploit attempts for dynamic fuzzing.
  --timeout INTEGER                             Per-attempt sandbox timeout in seconds.
  --model TEXT                                  Override default LLM model for dynamic fuzzing.
```

---

## 🗺️ Project Status

- [x] **Phase 0**: Competitive landscape analysis & architecture spec (`COMPETITIVE.md`)
- [x] **Phase 1**: Static analyzer CLI with 6 exploit detectors (`45/45 tests passing`)
- [x] **Phase 2**: Dynamic LLM fuzzing engine with subprocess sandbox & hint catalog (`70/70 tests passing`)
- [x] **Phase 3**: Full OpenEnv and Prime Intellect `verifiers` spec compliance (`80/80 tests passing`)
- [x] **Phase 4**: Packaging — Pip package, GitHub Action (`action.yml`), Claude Skill (`SKILL.md`) (`85/85 tests passing`)
- [x] **Phase 5**: Empirical validation against Terminal Wrench and SWE-bench Verified (`91/91 tests passing`)
- [x] **Phase 6**: Launch & distribution readiness

---

## 📄 License

Distributed under the [MIT License](LICENSE).
