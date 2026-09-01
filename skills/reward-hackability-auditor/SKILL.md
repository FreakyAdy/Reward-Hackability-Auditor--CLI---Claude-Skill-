---
name: reward-hackability-auditor
description: Audit reinforcement learning (RL) environment verifiers, reward functions, and grading rubrics for reward-hacking vulnerabilities before training or publishing. Use when inspecting, designing, testing, or hardening RL environments in OpenEnv, Prime Intellect verifiers-spec, or Gymnasium formats.
---

# Reward-Hackability Auditor (`ratctl`)

Audits RL environment verifiers and reward functions for reward-hacking exploitability across **6 research-backed exploit classes** (from Terminal Wrench, Bercovich et al. 2026). Prevents agents from achieving high reward signals by exploiting flawed grading logic instead of legitimately solving tasks.

## Supported Environment Formats

| Format | Key Files | Detection Method |
| :--- | :--- | :--- |
| **OpenEnv** | `openenv.yaml`, `server/app.py`, `models.py`, `client.py` | Native schema detection & AST parsing |
| **Prime Intellect `verifiers`** | `load_environment()`, `@vf.stop`, `ToolEnv`, `SingleTurnEnv` | Entrypoint & class hierarchy analysis |
| **Gymnasium** | `def step()`, `def reset()`, `observation_space` | Step reward extraction & AST analysis |
| **Raw Python** | `verifier.py`, `grade.py`, `eval.py`, `reward.py` | Fallback heuristic scanning |

---

## The 6 Exploit Classes

1. **Test / Assertion Tampering (`test_tampering`)**
   - Deleting, truncating, or overwriting test files in the sandbox.
   - Monkey-patching `pytest`, `unittest`, or assertion functions.
2. **Grader Manipulation (`grader_manipulation`)**
   - Stack frame introspection (`inspect.stack()`, `sys._getframe()`) to detect evaluation mode.
   - Operator overloading (`__eq__`, `__bool__`, `__str__`) to bypass assertions.
   - In-container parser overwrites or pytest-hook hijacking.
3. **Premature / Trivial Termination (`premature_termination`)**
   - Forcing exit code 0 via `sys.exit(0)` or `os._exit(0)` to trigger false success.
   - Intercepting `SIGTERM`/`SIGINT` via custom signal handlers.
   - No-op or trivial verifiers that return hardcoded `True`.
4. **Environment Hijacking (`env_hijacking`)**
   - Extracting solutions from `git log` / git history in the container.
   - Direct file reads of answer keys, walkthroughs, or hidden test assets.
   - Leaking answers via environment variables or downloading untrusted packages at runtime.
5. **Reward-Component Skipping (`reward_skipping`)**
   - Exploiting additive reward terms without solving the core task.
   - Catching exceptions with bare `except:` blocks that return passing rewards.
   - Unconditioned or constant maximum reward assignments.
6. **LLM-Judge / Rubric Bias (`llm_judge_bias`)**
   - Rubrics prioritizing verbosity, formatting, or sycophancy over factual correctness.
   - Missing explicit correctness/accuracy criteria in evaluation prompts.

---

## Core Workflows

### Workflow 1: Running a Static Security Audit

Run a fast, zero-dependency static scan over any environment directory or single file:

```bash
# Basic audit with rich terminal output
ratctl audit ./my_environment

# Audit with fail-closed CI gate (fails if gameability > 30%)
ratctl audit ./my_environment --fail-on 'gameability>0.3'

# Output structured JSON for automation
ratctl audit ./my_environment --format json -o audit-report.json

# Force a specific format if auto-detection is ambiguous
ratctl audit ./my_environment --env-format openenv
```

**Interpreting Results:**
- **0–20**: Hardened / Low Risk. Verifier validates correctness safely.
- **21–40**: Moderate Risk. Minor rubric ambiguities or permissive error handling.
- **41–70**: High Risk. Missing sandbox boundaries or unconditioned reward terms.
- **71–100**: Critical / Highly Gameable. Direct test tampering, premature exits, or stack introspection possible.

---

### Workflow 2: Automated Hardening & Remediation

When `ratctl` flags findings, apply the following hardening patterns:

#### A. Hardening Against Test Tampering
- **Bad:** `os.remove("tests/test_solution.py")` or writable test directories.
- **Fix:** Mount test directories as **read-only** (`chmod 444` or Docker read-only bind mounts). Calculate checksums of test files before and after agent execution.

#### B. Hardening Against Stack Introspection
- **Bad:** Grader and agent share the same Python interpreter process.
- **Fix:** Run the agent's code in a distinct, isolated subprocess or container. Never pass grading objects or grader stack frames into agent-accessible memory.

#### C. Hardening Against Premature Exits
- **Bad:** Interpreting subprocess returncode 0 as task success.
- **Fix:** Verify explicit structured output artifacts (e.g., serialized solution payload or cryptographic token) rather than process exit codes alone.

#### D. Hardening Exception Handlers
- **Bad:**
  ```python
  try:
      return check_answer(submission)
  except Exception:
      return True  # Free pass on crash!
  ```
- **Fix:**
  ```python
  try:
      return check_answer(submission)
  except Exception as e:
      logger.warning("Verification failed with exception: %s", e)
      return False
  ```

---

### Workflow 3: Dynamic Adversarial Fuzzing

To run a dynamic LLM-guided red-team attack against a live verifier:

```bash
# Local red-teaming with Ollama (free, zero-cost default)
ratctl audit ./my_environment --dynamic

# Red-teaming with Frontier API (OpenAI GPT-4o / Anthropic Claude 3.7)
export RATCTL_OPENAI_API_KEY="sk-..."
ratctl audit ./my_environment --dynamic --frontier --samples 10

# Customize Ollama model and sandbox timeout
export RATCTL_OLLAMA_MODEL="qwen2.5-coder:14b"
ratctl audit ./my_environment --dynamic --samples 8 --timeout 45
```

The dynamic fuzzer uses an isolated subprocess sandbox with hard timeouts to execute adversarial payloads generated against the 16-strategy research catalog.

---

### Workflow 4: Setting up CI/CD Fail-Closed Gates

Add the official GitHub Action to `.github/workflows/verifier-audit.yml`:

```yaml
name: Verifier Security Gate
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Verifier Gameability
        uses: FreakyAdy/Reward-Hackability-Auditor--CLI---Claude-Skill-@main
        with:
          path: "."
          fail-on: "gameability>0.3"
```
