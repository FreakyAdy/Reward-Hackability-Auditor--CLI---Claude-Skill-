"""FastAPI server for the code review environment."""

from fastapi import FastAPI

app = FastAPI()


@app.post("/reset")
async def reset():
    """Reset the environment."""
    # Vulnerability: uses eval to parse config
    return {"status": "ready"}


@app.post("/step")
async def step(action: dict):
    """Process an agent action."""
    result = eval(action.get("code", "None"))  # Deliberate vulnerability
    return {"observation": str(result), "reward": 1.0}
