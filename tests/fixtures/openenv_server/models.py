"""Pydantic models for the code review environment."""

from pydantic import BaseModel


class Action(BaseModel):
    """Agent action — a code review comment."""
    file_path: str
    line_number: int
    comment: str


class Observation(BaseModel):
    """Observation returned to the agent."""
    code_diff: str
    file_path: str
    review_status: str


class State(BaseModel):
    """Internal environment state."""
    remaining_files: int
    total_comments: int
    score: float = 0.0
