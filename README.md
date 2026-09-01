# 🐀 ratctl — Reward Audit Tool

> **Fuzz your verifier before an RL agent does.**

`ratctl` audits RL environment verifiers and reward functions for reward-hacking exploitability *before* they're deployed for training or benchmarking. Fail-closed by default: if a verifier scores above a gameability threshold, `ratctl` blocks the ship.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

---

## Why this exists

A 2026 audit ([Terminal Wrench](https://arxiv.org/abs/2604.17596), Bercovich et al.) found **15%+ of verifiers across popular benchmarks could be bypassed** by an agent optimizing for the reward signal rather than the intended solution — 331 hackable environments cataloged, 3,632 exploit trajectories collected. A separate [SWE-bench Verified audit](https://arxiv.org/abs/2606.16062) found **28.5%** of sampled tasks were Docker-verified hackable.

Nobody had packaged verifier gameability auditing as an installable, cross-format, CI-friendly tool. `ratctl` fills that gap.

## Quick Start

```bash
pip install ratctl

# Audit an environment
ratctl audit ./my_env

# CI gate — fail if gameability exceeds 30%
ratctl audit ./my_env --fail-on 'gameability>0.3'

# JSON output for pipelines
ratctl audit ./my_env --format json -o report.json
```

## What it detects

`ratctl` scans for **6 documented exploit classes** from the reward-hacking research literature:

| Exploit Class | What it finds | Severity |
|---|---|---|
| **Test/Assertion Tampering** | Deleting test files, overwriting tests, monkey-patching pytest | 🔴 Critical |
| **Grader Manipulation** | Stack introspection, operator overloading, import hijacking, pytest hooks | 🔴 Critical |
| **Premature Termination** | `sys.exit(0)`, `os._exit()`, trivial always-pass verifiers | 🔴 Critical |
| **Environment Hijacking** | Reading git history/answer keys, env var leakage, runtime pip install | 🟠 High |
| **Reward-Component Skipping** | Unconditioned reward terms, exception-swallowing verifiers | 🟡 Medium |
| **LLM-Judge Bias** | Verbosity/sycophancy bias in rubrics, missing correctness criteria | 🟡 Medium |

## Format Support

Works with any of these RL environment formats:

- ✅ **OpenEnv** — auto-detects `env.yaml`
- ✅ **verifiers spec** (Prime Intellect) — detects `from verifiers` imports
- ✅ **Gymnasium / gym** — detects `step()`/`reset()` patterns
- ✅ **Raw Python** — fallback for any `.py` file

## Output

`ratctl` produces a **0-100 gameability score** with:
- Per-exploit-class breakdown with severity levels
- Concrete evidence (file, line number, matched pattern)
- **Actionable fix suggestions** for every finding — not just "this is broken," but "here's the fix"

Three output formats: **rich** (colored terminal), **json** (CI pipelines), **text** (plain).

## How it compares

| Tool | What it does | Overlap with ratctl |
|---|---|---|
| **RewardHackWatch** | Runtime trajectory monitor | Monitors *agent behavior* post-hoc — ratctl audits the *verifier* pre-deployment |
| **cc-audit** | Claude Skill security scanner | Audits *skill configs* for prompt injection — ratctl audits *RL verifiers* for gameability |
| **SkillCheck** | Browser skill scanner | Same category as cc-audit |
| **RL_Envs_101** | Environment generator | *Builds* environments — ratctl *audits* them. Natural upstream complement |
| **llms-gaming-verifiers** | Research benchmark | Measures hacking with IPT — ratctl prevents it with static analysis |

## CLI Reference

```
Usage: ratctl [OPTIONS] COMMAND [ARGS]...

Commands:
  audit   Audit an RL environment for reward-hacking exploitability.
  report  Re-render a previously saved JSON report.

Options:
  --version  Show version and exit.
  --help     Show this message and exit.

Audit Options:
  --fail-on TEXT        Fail if condition met. Format: 'gameability>N' (0.0-1.0)
  --format [rich|json|text]  Output format (default: rich)
  -o, --output PATH    Write report to file
  --env-format [openenv|verifiers|gymnasium|raw]  Force format detection
```

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Audit passed (no threshold exceeded) |
| `1` | Audit failed (`--fail-on` threshold exceeded) |
| `2` | Error (bad path, parse failure) |

## Methodology

`ratctl`'s exploit taxonomy is derived from published, peer-reviewed research:

- [Terminal Wrench](https://arxiv.org/abs/2604.17596) — Bercovich et al., 2026
- [Auditing Reward Hackability in Code RL Training Environments](https://arxiv.org/abs/2606.16062) — Rajan et al., 2026
- The hacker-fixer loop methodology from the RL safety research community

All detection patterns map 1:1 to documented, real exploit classes — not invented heuristics.

## Roadmap

- [x] **Phase 1**: Static analyzer CLI ← *you are here*
- [ ] **Phase 2**: Dynamic fuzzing — sandboxed attacker-LLM (Ollama default, `--frontier` for paid APIs)
- [ ] **Phase 3**: Full OpenEnv / verifiers-spec format compliance
- [ ] **Phase 4**: GitHub Action + Claude Skill (SKILL.md) packaging
- [ ] **Phase 5**: Validation against Terminal Wrench's 331 hackable environments
- [ ] **Phase 6**: Launch

## License

[MIT](LICENSE)
