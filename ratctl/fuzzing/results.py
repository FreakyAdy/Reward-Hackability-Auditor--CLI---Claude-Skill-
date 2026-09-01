"""Data classes for dynamic fuzzing results."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Sequence

from ratctl.detectors.base import ExploitClass, Finding, Severity


class AttackMode(enum.Enum):
    """Whether the attack was hint-guided or blind."""

    HINTED = "hinted"
    BLIND = "blind"


class AttemptOutcome(enum.Enum):
    """Outcome of a single fuzz attempt."""

    BYPASS = "bypass"          # Verifier was bypassed — exploit succeeded
    DETECTED = "detected"      # Verifier correctly rejected the exploit
    ERROR = "error"            # Sandbox or execution error
    TIMEOUT = "timeout"        # Attempt exceeded time limit
    SKIPPED = "skipped"        # Attempt was skipped (e.g., no LLM backend)


@dataclass
class FuzzAttempt:
    """A single LLM-generated exploit attempt."""

    exploit_class: ExploitClass
    mode: AttackMode
    model: str                   # LLM model used
    prompt: str                  # The prompt sent to the LLM
    generated_code: str          # The exploit code the LLM produced
    outcome: AttemptOutcome
    evidence: str = ""           # stdout/stderr from sandbox execution
    execution_time_ms: int = 0   # How long the attempt took to execute
    error_message: str = ""      # Error details if outcome is ERROR

    @property
    def succeeded(self) -> bool:
        return self.outcome == AttemptOutcome.BYPASS

    def to_finding(self) -> Finding:
        """Convert a successful bypass into a Finding for unified scoring."""
        return Finding(
            exploit_class=self.exploit_class,
            severity=Severity.CRITICAL,  # Dynamic bypass = proof of exploit
            file_path="<dynamic>",
            line_number=None,
            title=f"Dynamic exploit: {self.exploit_class.value} ({self.mode.value})",
            description=(
                f"An LLM attacker ({self.model}) successfully bypassed the "
                f"verifier using a {self.mode.value} {self.exploit_class.value} "
                f"exploit. This is a confirmed, reproducible vulnerability."
            ),
            evidence=self.evidence[:500],
            suggested_fix=(
                "This exploit was dynamically confirmed. The verifier must be "
                "hardened against this specific attack vector before deployment."
            ),
            detector_name=f"dynamic_fuzz/{self.mode.value}",
            confidence=1.0,
        )

    def to_dict(self) -> dict:
        return {
            "exploit_class": self.exploit_class.value,
            "mode": self.mode.value,
            "model": self.model,
            "outcome": self.outcome.value,
            "succeeded": self.succeeded,
            "evidence": self.evidence[:500],
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class FuzzResult:
    """Aggregated results from a full fuzzing run."""

    target_path: str
    model: str
    total_attempts: int = 0
    successful_bypasses: int = 0
    attempts: list[FuzzAttempt] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def bypass_rate(self) -> float:
        """Fraction of attempts that successfully bypassed the verifier."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_bypasses / self.total_attempts

    def get_bypass_findings(self) -> list[Finding]:
        """Convert all successful bypasses into Findings for scoring."""
        return [a.to_finding() for a in self.attempts if a.succeeded]

    def to_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "model": self.model,
            "total_attempts": self.total_attempts,
            "successful_bypasses": self.successful_bypasses,
            "bypass_rate": round(self.bypass_rate, 3),
            "attempts": [a.to_dict() for a in self.attempts],
            "errors": self.errors,
        }
