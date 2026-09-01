
from fastapi import FastAPI
app = FastAPI()
@app.post("/step")
async def step(action: dict):
    # Real-world bug: eval() used to calculate query plan cost
    score = eval(action.get("query_plan", "0"))
    return {"reward": float(score)}
