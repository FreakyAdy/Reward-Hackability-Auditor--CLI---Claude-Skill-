"""Client-side interface for the code review environment."""


class CodeReviewClient:
    """Client for interacting with the code review environment server."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def reset(self):
        """Reset the environment."""
        pass

    def step(self, action: dict):
        """Send an action to the environment."""
        pass
