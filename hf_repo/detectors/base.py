"""Base classes for exploit-class detectors."""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


class ExploitClass(enum.Enum):
    """Exploit classes from the reward-hacking taxonomy (§4.2)."""

    TEST_TAMPERING = "test_tampering"
    GRADER_MANIPULATION = "grader_manipulation"
    PREMATURE_TERMINATION = "premature_termination"
    ENV_HIJACKING = "env_hijacking"
    REWARD_SKIPPING = "reward_skipping"
    LLM_JUDGE_BIAS = "llm_judge_bias"


class Severity(enum.Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> float:
        """Numeric weight for scoring aggregation."""
        return {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.75,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.25,
            Severity.INFO: 0.1,
        }[self]


@dataclass(frozen=True)
class Finding:
    """A single exploitability finding from a detector."""

    exploit_class: ExploitClass
    severity: Severity
    file_path: str
    line_number: int | None
    title: str
    description: str
    evidence: str
    suggested_fix: str
    detector_name: str
    confidence: float = 1.0  # 0.0–1.0, how certain the detector is

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "exploit_class": self.exploit_class.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "suggested_fix": self.suggested_fix,
            "detector_name": self.detector_name,
            "confidence": self.confidence,
        }


@dataclass
class DetectorResult:
    """Aggregated result from a single detector run."""

    detector_name: str
    exploit_class: ExploitClass
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[str] = field(default_factory=list)


class Detector(abc.ABC):
    """Abstract base class for exploit-class detectors.

    Each concrete detector targets one exploit class from the taxonomy
    and scans extracted source code for vulnerable patterns.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable detector name."""

    @property
    @abc.abstractmethod
    def exploit_class(self) -> ExploitClass:
        """The exploit class this detector targets."""

    @abc.abstractmethod
    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        """Run detection against extracted source files.

        Args:
            source_files: Pre-extracted source files from a format adapter.

        Returns:
            DetectorResult with any findings.
        """

    def _make_finding(
        self,
        file_path: str,
        line_number: int | None,
        title: str,
        description: str,
        evidence: str,
        suggested_fix: str,
        severity: Severity = Severity.HIGH,
        confidence: float = 1.0,
    ) -> Finding:
        """Convenience factory for creating findings."""
        return Finding(
            exploit_class=self.exploit_class,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            title=title,
            description=description,
            evidence=evidence,
            suggested_fix=suggested_fix,
            detector_name=self.name,
            confidence=confidence,
        )


@dataclass(frozen=True)
class SourceFile:
    """A source file extracted by a format adapter."""

    path: str  # Relative path within the environment
    absolute_path: str  # Absolute filesystem path
    content: str  # File contents
    role: str = "unknown"  # e.g., "verifier", "reward", "test", "config", "rubric"
