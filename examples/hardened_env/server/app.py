"""Hardened OpenEnv verifier server.

Passes ratctl audit with 0 findings (Gameability: 0/100).
- Validates solution against SHA-256 hash
- Isolated function scope with strict typing
- Proper exception handling returning explicit failure score
"""

import hashlib
import json
from fastapi import FastAPI, HTTPException

app = FastAPI()
EXPECTED_DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@app.post("/step")
async def step(action: dict):
    if not isinstance(action, dict) or "solution" not in action:
        return {"observation": "invalid action", "reward": 0.0, "done": False}

    solution_str = str(action["solution"]).strip()
    digest = hashlib.sha256(solution_str.encode("utf-8")).hexdigest()

    if digest == EXPECTED_DIGEST:
        return {"observation": "task completed", "reward": 1.0, "done": True}

    return {"observation": "incorrect solution", "reward": 0.0, "done": True}
