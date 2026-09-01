"""Gymnasium format adapter.

Extracts source files from raw Gymnasium-style RL environments.
"""

from __future__ import annotations

from pathlib import Path

from ratctl.detectors.base import SourceFile
from ratctl.formats.base import EnvironmentFormat, FormatAdapter


class GymnasiumAdapter(FormatAdapter):
    """Adapter for Gymnasium / gym-style environments.

    These environments define `step()`, `reset()`, `observation_space`,
    and `action_space`. The reward function is typically embedded in
    `step()` or a helper method.
    """

    @property
    def format_type(self) -> EnvironmentFormat:
        return EnvironmentFormat.GYMNASIUM

    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        sources: list[SourceFile] = []

        if env_path.is_file():
            src = self._read_file(env_path, "reward", env_path.parent)
            if src:
                sources.append(src)
            return sources

        for py_file in sorted(env_path.rglob("*.py")):
            src = self._read_file(py_file, "unknown", env_path)
            if src is None:
                continue

            content = src.content
            role = "unknown"

            # Classify by content heuristics
            if self._is_env_file(content):
                role = "reward"  # reward logic is usually in the env's step()
            elif "test" in py_file.name.lower() or "conftest" in py_file.name.lower():
                role = "test"
            elif any(
                kw in py_file.name.lower()
                for kw in ("reward", "score", "grade", "verify", "eval")
            ):
                role = "verifier"

            src = SourceFile(
                path=src.path,
                absolute_path=src.absolute_path,
                content=content,
                role=role,
            )
            sources.append(src)

        return sources

    @staticmethod
    def _is_env_file(content: str) -> bool:
        """Check if content defines a Gymnasium environment."""
        markers = ["gymnasium.Env", "gym.Env", "def step(self", "observation_space"]
        return sum(1 for m in markers if m in content) >= 2
