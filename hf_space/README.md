---
title: ratctl — Reward-Hackability Auditor for RL Verifiers
emoji: 🐀
colorFrom: red
colorTo: purple
sdk: static
pinned: false
license: mit
short_description: Audit RL verifiers & reward functions for exploits.
---

# 🐀 ratctl — Reward-Hackability Auditor

Audits RL environment verifiers, reward functions, and grading harnesses for reward-hacking vulnerabilities across 6 exploit classes.

## ⚠️ Demo Scope

This Hugging Face Space is a **browser-based JavaScript port** of ratctl's regex detection engine. It runs entirely client-side — no server required.

### ✅ What this demo covers

| Feature | Status |
| :--- | :---: |
| All 6 exploit class detectors (regex patterns) | ✅ |
| Scoring engine (weighted gameability score) | ✅ |
| Finding details with severity, evidence & remediation | ✅ |
| Interactive code editing with preset examples | ✅ |
| Glassmorphic dashboard UI | ✅ |

### ❌ What requires the full CLI (`pip install ratctl`)

| Feature | Status |
| :--- | :---: |
| Deep AST-based analysis (Python syntax tree) | CLI only |
| Multi-file / directory scanning | CLI only |
| Format auto-detection (OpenEnv, verifiers, Gymnasium) | CLI only |
| Dynamic LLM red-team fuzzing (Ollama / GPT-4o) | CLI only |
| CI/CD gate (`--fail-on 'gameability>0.3'`) | CLI only |
| Live in-training monitoring (`ratctl watch`) | CLI only |
| JSON / Rich / Text report formats | CLI only |

## 🚀 Get the full tool

```bash
pip install ratctl
ratctl audit ./my_environment --fail-on 'gameability>0.3'
```

## 📚 Links

- 📦 GitHub: [FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-](https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-)
- 📄 Empirical Study: Audited 112 public RL post-training environments — 61.6% vulnerability rate
- 📋 Technical Report: [PAPER.md](https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-/blob/main/PAPER.md)
