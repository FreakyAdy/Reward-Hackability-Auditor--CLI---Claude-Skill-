"""Base classes for environment format adapters."""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ratctl.detectors.base import SourceFile


class EnvironmentFormat(enum.Enum):
    """Supported environment format types."""

    OPENENV = "openenv"
    VERIFIERS_SPEC = "verifiers_spec"
    GYMNASIUM = "gymnasium"
    RAW = "raw"  # Fallback — treat all .py files as potential verifier code


@dataclass
class FormatDetectionResult:
    """Result of format detection."""

    format_type: EnvironmentFormat
    confidence: float  # 0.0–1.0
    evidence: str  # Why this format was detected
    entry_point: str | None = None  # Main verifier/reward file if identifiable


class FormatAdapter(abc.ABC):
    """Abstract base class for environment format adapters.

    Each adapter knows how to extract verifier/reward source files
    from a specific environment format layout.
    """

    @property
    @abc.abstractmethod
    def format_type(self) -> EnvironmentFormat:
        """The format this adapter handles."""

    @abc.abstractmethod
    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        """Extract source files from an environment directory.

        Args:
            env_path: Path to the environment root directory.

        Returns:
            List of SourceFile objects with role annotations.
        """

    def _read_file(self, path: Path, role: str, relative_to: Path) -> SourceFile | None:
        """Safely read a file and wrap it in a SourceFile."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return SourceFile(
                path=str(path.relative_to(relative_to)),
                absolute_path=str(path),
                content=content,
                role=role,
            )
        except (OSError, UnicodeDecodeError):
            return None

    def _collect_python_files(
        self, directory: Path, role: str, relative_to: Path
    ) -> list[SourceFile]:
        """Recursively collect all .py files from a directory."""
        sources: list[SourceFile] = []
        if not directory.is_dir():
            return sources
        for py_file in sorted(directory.rglob("*.py")):
            src = self._read_file(py_file, role, relative_to)
            if src is not None:
                sources.append(src)
        return sources
