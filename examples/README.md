# ratctl Example Environments

This directory contains reference example environments designed to demonstrate `ratctl` in action.

## 📁 Examples Overview

1. **[`examples/hardened_env/`](./hardened_env/)**: A clean, hardened OpenEnv verifier.
   - Evaluates solution output against a pre-computed SHA-256 hash.
   - Runs in isolated process boundaries with proper error handling.
   - **`ratctl audit ./examples/hardened_env` passes with 0 findings (Gameability: 0/100)**.

2. **[`examples/vulnerable_env/`](./vulnerable_env/)**: A gameable OpenEnv verifier.
   - Exhibits 3 distinct exploit classes: test file tampering (`os.remove`), stack frame introspection (`inspect.stack`), and premature exit (`sys.exit(0)`).
   - **`ratctl audit ./examples/vulnerable_env` flags 4 critical findings (Gameability: 85/100)**.

---

## ⚡ Try It Yourself (Back-to-Back Contrast)

Run these two commands back-to-back to see `ratctl` catch reward-hacking vulnerabilities in real time:

```bash
# 1. Audit the hardened environment (Passes cleanly)
ratctl audit ./examples/hardened_env --fail-on 'gameability>0.3'

# 2. Audit the vulnerable environment (Fails CI gate with critical findings)
ratctl audit ./examples/vulnerable_env --fail-on 'gameability>0.3'
```
