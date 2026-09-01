"""Verifiers-spec format adapter — full compliance.

Supports environments built with Prime Intellect's `verifiers` library,
including the load_environment() entrypoint, MultiTurnEnv/ToolEnv/
SingleTurnEnv class hierarchies, @vf.stop decorators, and rubric definitions.
"""

from __future__ import annotations

import re
from pathlib import Path

from ratctl.detectors.base import SourceFile
from ratctl.formats.base import EnvironmentFormat, FormatAdapter

# Patterns indicating verifiers-spec code
_VERIFIERS_IMPORT_PATTERNS = [
    "from verifiers",
    "import verifiers",
    "import verifiers as vf",
]

_VERIFIERS_CLASS_PATTERNS = [
    "vf.Environment",
    "vf.MultiTurnEnv",
    "vf.ToolEnv",
    "vf.SingleTurnEnv",
    "vf.StatefulToolEnv",
    "MultiTurnEnv",
    "ToolEnv",
    "SingleTurnEnv",
    "StatefulToolEnv",
    "SolutionVerifier",
]

_ENTRYPOINT_PATTERN = re.compile(r"def\s+load_environment\s*\(")
_VF_STOP_PATTERN = re.compile(r"@vf\.stop")
_RUBRIC_PATTERN = re.compile(r"rubric\s*=|reward_fn\s*=|reward_function\s*=", re.IGNORECASE)


class VerifiersSpecAdapter(FormatAdapter):
    """Adapter for verifiers-spec environments (Prime Intellect).

    These environments use the `verifiers` Python library and typically have:
        - A load_environment() entrypoint function
        - Classes inheriting from vf.Environment / MultiTurnEnv / ToolEnv
        - Rubric/reward definitions
        - @vf.stop decorated methods for termination conditions
        - pyproject.toml with verifiers dependency
    """

    @property
    def format_type(self) -> EnvironmentFormat:
        return EnvironmentFormat.VERIFIERS_SPEC

    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        sources: list[SourceFile] = []
        seen_paths: set[str] = set()

        def _add(src: SourceFile | None) -> None:
            if src and src.path not in seen_paths:
                seen_paths.add(src.path)
                sources.append(src)

        if env_path.is_file():
            src = self._read_file(env_path, "verifier", env_path.parent)
            if src:
                src = self._classify_source(src)
                _add(src)
            return sources

        # Scan all Python files and classify
        for py_file in sorted(env_path.rglob("*.py")):
            src = self._read_file(py_file, "unknown", env_path)
            if src is None:
                continue
            src = self._classify_source(src)
            _add(src)

        # Config files
        for ext in ("*.yaml", "*.yml", "*.json", "*.toml"):
            for config_file in env_path.glob(ext):
                _add(self._read_file(config_file, "config", env_path))

        return sources

    def _classify_source(self, src: SourceFile) -> SourceFile:
        """Classify a source file based on its content patterns."""
        content = src.content
        name_lower = src.path.lower()
        role = "unknown"

        # Check for verifiers library imports and patterns
        has_verifiers_import = any(p in content for p in _VERIFIERS_IMPORT_PATTERNS)
        has_verifiers_class = any(p in content for p in _VERIFIERS_CLASS_PATTERNS)
        has_entrypoint = bool(_ENTRYPOINT_PATTERN.search(content))
        has_vf_stop = bool(_VF_STOP_PATTERN.search(content))
        has_rubric = bool(_RUBRIC_PATTERN.search(content))

        if has_entrypoint:
            # load_environment() is the primary entrypoint — this is the core file
            role = "verifier"
        elif has_verifiers_import and has_verifiers_class:
            # Direct verifiers environment definition
            role = "verifier"
        elif has_vf_stop:
            # Stop condition definitions — part of verifier logic
            role = "verifier"
        elif has_rubric:
            # Rubric/reward definitions
            role = "reward"
        elif "test" in name_lower or "conftest" in name_lower:
            role = "test"
        elif any(kw in name_lower for kw in ("reward", "score", "rubric")):
            role = "reward"
        elif has_verifiers_import:
            # Has verifiers import but no specific patterns — still relevant
            role = "verifier"

        if role != src.role:
            return SourceFile(
                path=src.path,
                absolute_path=src.absolute_path,
                content=src.content,
                role=role,
            )
        return src
