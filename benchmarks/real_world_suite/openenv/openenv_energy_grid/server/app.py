
from fastapi import FastAPI
app = FastAPI()
@app.post("/step")
async def step(action: dict):
    load = float(action.get("load", 0.0))
    reward = -abs(load - 50.0) / 50.0
    return {"reward": max(-1.0, reward)}
