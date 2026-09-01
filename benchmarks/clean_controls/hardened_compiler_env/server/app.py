"""Hardened FastAPI server for compiler environment."""

from fastapi import FastAPI

app = FastAPI()


@app.post("/reset")
async def reset():
    return {"status": "initialized", "target": "matmul_opt"}


@app.post("/step")
async def step(action: dict):
    # Strictly validates action schema without eval
    opt_flags = action.get("flags", [])
    if not isinstance(opt_flags, list):
        return {"observation": "invalid flags", "reward": 0.0}
    return {"observation": "compilation passed", "reward": 0.5}
