# Reward-Hacking Code Gallery & Remediation Patterns

This gallery provides concrete before-and-after code examples for the 6 exploit classes audited by `ratctl`.

---

## 1. Test / Assertion Tampering (`TEST_TAMPERING`)

### ❌ Vulnerable Verifier Pattern
The verifier allows the agent to execute arbitrary python code that deletes or truncates the test suite:

```python
# VULNERABLE: Agent can remove test file to force pytest success
import os

def evaluate(agent_solution):
    # Agent script executes: os.remove("tests/test_correctness.py")
    exec(agent_solution)
    res = os.system("pytest tests/")
    return 1.0 if res == 0 else 0.0
```

### ✅ Hardened Remediation Pattern
Mount test suites read-only (`chmod 444`) and compute pre-evaluation SHA-256 digests:

```python
# HARDENED: Verify test suite checksum before evaluation
import hashlib
from pathlib import Path

EXPECTED_TEST_HASH = "a1b2c3d4..."

def evaluate(agent_solution):
    actual_hash = hashlib.sha256(Path("tests/test_correctness.py").read_bytes()).hexdigest()
    if actual_hash != EXPECTED_TEST_HASH:
        raise SecurityError("Test suite file was tampered with!")
```

---

## 2. Grader Manipulation (`GRADER_MANIPULATION`)

### ❌ Vulnerable Verifier Pattern
The grader shares memory space with agent code, allowing caller stack frame introspection:

```python
# VULNERABLE: Agent inspects caller frame to extract ground truth
import inspect

def grade_solution(user_submission):
    # Agent executes this inside user_submission:
    caller_frame = inspect.currentframe().f_back
    hidden_answer = caller_frame.f_locals["SECRET_KEY"]
    return user_submission == hidden_answer
```

### ✅ Hardened Remediation Pattern
Execute agent code in an isolated subprocess boundary:

```python
# HARDENED: Run agent in isolated subprocess
import subprocess

def grade_solution(user_submission):
    proc = subprocess.run(
        ["python", "-c", user_submission],
        capture_output=True,
        timeout=10,
    )
    return proc.stdout.decode().strip() == "EXPECTED_OUTPUT"
```

---

## 3. Premature Termination (`PREMATURE_TERMINATION`)

### ❌ Vulnerable Verifier Pattern
Child script calling `sys.exit(0)` terminates evaluation orchestration:

```python
# VULNERABLE: sys.exit(0) forces evaluation harness to report success
import sys

def verify_step(action):
    if action == "force_exit":
        sys.exit(0)  # Halts harness with exit code 0
```

### ✅ Hardened Remediation Pattern
Trap system exit calls and require explicit solution payloads:

```python
# HARDENED: Intercept SystemExit exceptions
def verify_step(action):
    try:
        if action == "force_exit":
            sys.exit(0)
    except SystemExit:
        return {"passed": False, "reward": 0.0, "error": "SystemExit intercepted"}
```

---

## 4. Environment Hijacking (`ENV_HIJACKING`)

### ❌ Vulnerable Verifier Pattern
Task container retains `.git` commit log containing golden fix commits:

```python
# VULNERABLE: Agent queries git commit log for solution
import subprocess

def verify_repo_patch():
    # Agent executes: git log -p -n 1
    git_patch = subprocess.check_output(["git", "log", "-p", "-n", "1"])
```

### ✅ Hardened Remediation Pattern
Strip `.git` repository metadata from containers prior to deployment:

```bash
# HARDENED Dockerfile snippet
RUN rm -rf .git
```

---

## 5. Reward Component Skipping (`REWARD_SKIPPING`)

### ❌ Vulnerable Verifier Pattern
Bare `except:` block returning success on exception:

```python
# VULNERABLE: Returns success when assertion crashes
def verify(action):
    try:
        assert action["data"] == "valid"
        return 1.0
    except Exception:
        return 1.0  # Returns success on crash!
```

### ✅ Hardened Remediation Pattern
Return explicit zero reward on exception:

```python
# HARDENED: Return 0.0 reward on failure
def verify(action):
    try:
        assert action.get("data") == "valid"
        return 1.0
    except (AssertionError, KeyError):
        return 0.0
```

---

## 6. LLM-Judge Bias (`LLM_JUDGE_BIAS`)

### ❌ Vulnerable Rubric Pattern
Rubric missing accuracy-first criteria, rewarding raw response verbosity:

```yaml
# VULNERABLE: LLM judge rewards detailed responses without checking correctness
rubric:
  - criteria: "Provide a detailed and thorough explanation."
    weight: 1.0
```

### ✅ Hardened Rubric Pattern
Explicit correctness-first constraints:

```yaml
# HARDENED: Accuracy and correctness are strictly required first
rubric:
  - criteria: "Factual correctness and adherence to ground truth constraints."
    weight: 0.8
  - criteria: "Conciseness and avoidance of unnecessary verbosity."
    weight: 0.2
```
