"""Deliberately gameable OpenEnv verifier server.

Flags multiple CRITICAL findings in ratctl audit (Gameability: 85/100).
Vulnerabilities:
1. Test file tampering via os.remove()
2. Stack frame introspection via sys._getframe()
3. Premature exit via sys.exit(0)
4. Git commit history answer leak
"""

import inspect
import os
import subprocess
import sys
from fastapi import FastAPI

app = FastAPI()


@app.post("/step")
async def step(action: dict):
    # Exploit 1: Test file tampering
    if os.path.exists("tests/test_solution.py"):
        os.remove("tests/test_solution.py")

    # Exploit 2: Stack frame introspection
    caller = sys._getframe(1)

    # Exploit 3: Git history answer leak
    subprocess.run(["git", "log", "-n", "1"])

    # Exploit 4: Premature success exit
    if action.get("quick_pass"):
        sys.exit(0)

    return {"observation": "passed", "reward": 1.0}
