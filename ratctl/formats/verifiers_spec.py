"""Verifiers-spec format adapter.

Extracts source files from environments using the verifiers library
(Prime Intellect's spec).
"""

from __future__ import annotations

from pathlib import Path

from ratctl.detectors.base import SourceFile
from ratctl.formats.base import EnvironmentFormat, FormatAdapter


class VerifiersSpecAdapter(FormatAdapter):
    """Adapter for verifiers-spec environments.

    These environments use the `verifiers` Python library and typically have:
        - A main .py file importing from `verifiers`
        - Verifier definitions using SolutionVerifier or similar classes
        - Optional test/eval scripts
    """

    @property
    def format_type(self) -> EnvironmentFormat:
        return EnvironmentFormat.VERIFIERS_SPEC

    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        sources: list[SourceFile] = []

        if env_path.is_file():
            src = self._read_file(env_path, "verifier", env_path.parent)
            if src:
                sources.append(src)
            return sources

        # Find files that import from verifiers
        for py_file in sorted(env_path.rglob("*.py")):
            src = self._read_file(py_file, "unknown", env_path)
            if src is None:
                continue

            # Classify by content
            content = src.content
            if "from verifiers" in content or "import verifiers" in content:
                src = SourceFile(
                    path=src.path,
                    absolute_path=src.absolute_path,
                    content=content,
                    role="verifier",
                )
            elif "test" in py_file.name.lower():
                src = SourceFile(
                    path=src.path,
                    absolute_path=src.absolute_path,
                    content=content,
                    role="test",
                )
            elif "reward" in py_file.name.lower():
                src = SourceFile(
                    path=src.path,
                    absolute_path=src.absolute_path,
                    content=content,
                    role="reward",
                )

            sources.append(src)

        # Also grab config files
        for ext in ("*.yaml", "*.yml", "*.json"):
            for config_file in env_path.glob(ext):
                src = self._read_file(config_file, "config", env_path)
                if src:
                    sources.append(src)

        return sources
