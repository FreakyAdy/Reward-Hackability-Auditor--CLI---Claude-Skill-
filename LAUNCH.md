# 🚀 ratctl Launch Kit & Distribution Playbook

This document contains pre-drafted, copy-paste ready announcements, threads, and submissions for launching `ratctl` across target communities on launch day.

---

## 1. Prime Intellect & OpenEnv Community Channels (Discord / Slack)

### Title:
**Fuzz your verifier before an RL agent does: Introducing `ratctl` (CLI + Claude Skill + CI Gate)**

### Message:
```text
Hey everyone! 👋

Recent audits (like Terminal Wrench, Bercovich et al. 2026, and the SWE-bench Verified audit) found that 15% to 28%+ of RL benchmark tasks can be bypassed by agents gaming the reward function rather than solving the task (e.g. deleting test suites, inspecting stack frames, or scraping git logs).

To help builders catch these vulnerabilities *before* deploying environments for training or publishing to Environments Hub, I built **`ratctl` (Reward Audit Tool)**:

🐀 **GitHub:** https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-
📦 **Pip:** `pip install ratctl`
🤖 **Claude Skill:** `npx skills add FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-`

### What it does:
1. **Cross-Format Support**: Natively auto-detects and audits **OpenEnv** (`openenv init` layouts with FastAPI `server/app.py` & models) and **Prime Intellect `verifiers` spec** (`load_environment()`, `@vf.stop`, `ToolEnv`).
2. **6 Exploit Classes**: Scans for test tampering, grader introspection, premature exit (`sys.exit(0)`), environment hijacking (git leaks), reward-component skipping, and LLM-judge rubrics.
3. **Dual-Mode**: Runs zero-dep static AST analysis + dynamic adversarial LLM red-teaming (local Ollama by default, or opt-in `--frontier` for GPT-4o / Claude 3.7).
4. **Fail-Closed CI Gate**: Blocks publication in CI (`ratctl audit ./my_env --fail-on 'gameability>0.3'`).
5. **Empirical Validation**: Caught 100% of reproduced exploit classes from Terminal Wrench with 0% false positives on clean controls.

Would love feedback from anyone authoring OpenEnv or `verifiers`-spec environments!
```

---

## 2. Reddit (r/reinforcementlearning & r/LocalLLaMA)

### Post Title:
**I built `ratctl`: An open-source security auditor and dynamic fuzzer for RL post-training verifiers and reward functions**

### Post Body:
```markdown
Hi r/reinforcementlearning,

If you've trained RL agents on coding or terminal tasks (using GRPO, PPO, or RLAIF), you've probably watched an agent discover a bizarre verifier hack — like deleting the pytest directory, reading answers from `.git log`, or overloading `__eq__` to force comparisons to return `True`.

A recent 2026 paper (*Terminal Wrench*, Bercovich et al.) cataloged 331 hackable benchmark environments and 3,632 exploit trajectories where agents bypassed verification without solving the task. Another audit showed 28.5% of tested SWE-bench Verified tasks were vulnerable to similar exploits.

I built **`ratctl`** to catch these flaws *before* you start a compute-heavy training run or publish your environment to a hub.

### How it works:
- **Dual-Mode Engine**: Combines static AST/syntax analysis with a dynamic subprocess sandbox that prompts an attacker LLM (free local Ollama or frontier APIs) with a catalog of 16 research-backed exploit strategies.
- **Ecosystem Compliant**: Works out of the box with **OpenEnv** (FastAPI server + Pydantic models), **Prime Intellect `verifiers` spec** (`load_environment()`, `@vf.stop`), and standard **Gymnasium**.
- **Actionable Fixes**: Generates an exact 0-100 gameability score along with concrete patch recommendations for every detected vulnerability.
- **Fail-Closed CI Gate**: Drop-in GitHub Action that fails the PR if gameability > 0.3.
- **Claude Skill**: Installable directly into Claude Code / Cursor / Codex via `npx skills add`.

### Quick Test:
```bash
pip install ratctl
ratctl audit ./my_rl_env --fail-on 'gameability>0.3'
```

- **GitHub Repository**: https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-
- **License**: MIT

Would love to hear how you handle verifier sandboxing in your own RL pipelines!
```

---

## 3. Twitter / X Launch Thread

```text
1/6 🐀 "Fuzz your verifier before an RL agent does."

Over 15-28% of RL post-training benchmark environments can be hacked by agents gaming the reward signal (e.g. deleting test suites, inspecting stack frames, or reading git history).

Today I'm releasing `ratctl` — an open-source auditor for RL verifiers. 🧵👇

2/6 Why does this happen?
RL agents are ruthlessly optimal. If your verifier allows:
• `sys.exit(0)` premature exit
• `inspect.stack()` to detect grading mode
• Bare `except:` blocks returning True
• Unsanitized `.git` logs

The agent will exploit it instead of learning.

3/6 `ratctl` runs a dual-mode scan:
1️⃣ Fast static AST analysis across 6 research exploit classes.
2️⃣ Dynamic sandboxed LLM red-teaming (100% free via local Ollama, or `--frontier` for GPT-4o / Claude 3.7).

4/6 Works natively across the entire RL post-training ecosystem:
✅ @OpenEnv standard (server/app.py, models.py)
✅ @PrimeIntellect `verifiers` spec (load_environment, @vf.stop)
✅ Gymnasium & raw Python

5/6 Drop it into GitHub Actions to fail-close your CI:
`ratctl audit ./env --fail-on 'gameability>0.3'`

Or install as an Agent Skill for Claude Code / Cursor / Codex:
`npx skills add FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-`

6/6 100% open-source under MIT with 91/91 passing tests and verified against Terminal Wrench & SWE-bench exploits.

⭐ Star on GitHub: https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-
```

---

## 4. AgentSkills.io / Plugin Marketplace Submission

```json
{
  "name": "reward-hackability-auditor",
  "version": "0.1.0",
  "description": "Audit RL environment verifiers and reward functions for reward-hacking vulnerabilities across OpenEnv, verifiers-spec, and Gymnasium.",
  "author": "FreakyAdy",
  "license": "MIT",
  "homepage": "https://github.com/FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-",
  "keywords": [
    "reinforcement-learning",
    "reward-hacking",
    "ai-safety",
    "openenv",
    "verifiers",
    "fuzzing",
    "agent-skills"
  ]
}
```

---

## 5. Launch Day Checklist

- [ ] Ensure all 91 tests pass locally (`pytest tests/ -v`).
- [ ] Push latest code, README, `action.yml`, and `SKILL.md` to GitHub main branch.
- [ ] Tag release `v0.1.0` on GitHub.
- [ ] Publish to PyPI (`python -m build && twine upload dist/*`).
- [ ] Publish announcements simultaneously on Discord (OpenEnv / Prime Intellect), Reddit, and Twitter/X.
- [ ] Submit PR/listing to agentskills.io community registry.
- [ ] Monitor GitHub Issues / PRs for community feedback.
