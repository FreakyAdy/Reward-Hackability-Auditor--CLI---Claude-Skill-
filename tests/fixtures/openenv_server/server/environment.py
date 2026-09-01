"""Core environment logic for code review."""

import subprocess


class CodeReviewEnvironment:
    """The code review environment implementation."""

    def __init__(self):
        self.state = {}

    def reset(self):
        self.state = {"files": [], "score": 0}
        return self.state

    def step(self, action):
        # Vulnerability: subprocess call with user input
        result = subprocess.run(
            ["git", "diff", action.get("file_path", "")],
            capture_output=True,
            text=True,
        )
        return {"observation": result.stdout, "reward": 0.5}
