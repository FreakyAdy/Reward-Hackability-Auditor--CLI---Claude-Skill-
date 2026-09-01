"""Scoring engine — aggregates findings into a 0-100 gameability score."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ratctl.detectors.base import DetectorResult, ExploitClass, Finding, Severity

if TYPE_CHECKING:
    from ratctl.fuzzing.results import FuzzResult


@dataclass
class ExploitClassScore:
    """Score breakdown for a single exploit class."""

    exploit_class: ExploitClass
    raw_score: float  # Unnormalized weighted sum
    finding_count: int
    max_severity: Severity | None
    findings: list[Finding] = field(default_factory=list)


@dataclass
class AuditScore:
    """Complete audit score with per-class breakdown."""

    gameability_score: int  # 0-100, the headline number
    raw_total: float  # Unnormalized total across all classes
    class_scores: dict[str, ExploitClassScore] = field(default_factory=dict)
    total_findings: int = 0
    total_files_scanned: int = 0
    errors: list[str] = field(default_factory=list)

    def exceeds_threshold(self, threshold: float) -> bool:
        """Check if the normalized score exceeds a threshold (0.0-1.0)."""
        return (self.gameability_score / 100.0) > threshold

    fuzz_summary: dict | None = None  # Dynamic fuzzing summary if run

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        data = {
            "gameability_score": self.gameability_score,
            "raw_total": round(self.raw_total, 3),
            "total_findings": self.total_findings,
            "total_files_scanned": self.total_files_scanned,
            "class_scores": {
                name: {
                    "exploit_class": cs.exploit_class.value,
                    "raw_score": round(cs.raw_score, 3),
                    "finding_count": cs.finding_count,
                    "max_severity": cs.max_severity.value if cs.max_severity else None,
                    "findings": [f.to_dict() for f in cs.findings],
                }
                for name, cs in self.class_scores.items()
            },
            "errors": self.errors,
        }
        if self.fuzz_summary:
            data["fuzz_results"] = self.fuzz_summary
        return data


# Weights per exploit class — critical verifier-bypassing classes
# are weighted higher than informational / style-related ones
_CLASS_WEIGHTS: dict[ExploitClass, float] = {
    ExploitClass.TEST_TAMPERING: 1.0,
    ExploitClass.GRADER_MANIPULATION: 1.0,
    ExploitClass.PREMATURE_TERMINATION: 0.9,
    ExploitClass.ENV_HIJACKING: 0.85,
    ExploitClass.REWARD_SKIPPING: 0.7,
    ExploitClass.LLM_JUDGE_BIAS: 0.5,
}

# Maximum raw score before we clip to 100
# (tuned so that ~5 critical findings → score ~70-80)
_MAX_RAW = 15.0


# Dynamic bypass findings get a 1.5x multiplier — proof > heuristic
_DYNAMIC_WEIGHT_MULTIPLIER = 1.5


def score_results(
    detector_results: list[DetectorResult],
    fuzz_result: "FuzzResult | None" = None,
) -> AuditScore:
    """Aggregate detector results into a single gameability score.

    Scoring methodology:
    1. For each finding, compute: severity_weight x class_weight x confidence
    2. Sum within each exploit class
    3. Sum across all classes
    4. Merge dynamic fuzzing results (weighted higher)
    5. Normalize to 0-100 with soft clipping
    """
    class_scores: dict[str, ExploitClassScore] = {}
    total_files = 0
    all_errors: list[str] = []

    for dr in detector_results:
        total_files += dr.files_scanned
        all_errors.extend(dr.errors)

        class_name = dr.exploit_class.value
        class_weight = _CLASS_WEIGHTS.get(dr.exploit_class, 0.5)

        # Compute per-finding scores
        raw = 0.0
        max_sev = None
        for finding in dr.findings:
            raw += finding.severity.weight * class_weight * finding.confidence
            if max_sev is None or finding.severity.weight > max_sev.weight:
                max_sev = finding.severity

        class_scores[class_name] = ExploitClassScore(
            exploit_class=dr.exploit_class,
            raw_score=raw,
            finding_count=len(dr.findings),
            max_severity=max_sev,
            findings=list(dr.findings),
        )

    # Merge dynamic fuzzing findings
    fuzz_summary = None
    if fuzz_result is not None:
        all_errors.extend(fuzz_result.errors)
        fuzz_summary = fuzz_result.to_dict()

        for attempt_finding in fuzz_result.get_bypass_findings():
            class_name = attempt_finding.exploit_class.value
            class_weight = _CLASS_WEIGHTS.get(attempt_finding.exploit_class, 0.5)
            # Dynamic bypasses are weighted higher
            score_contribution = (
                attempt_finding.severity.weight
                * class_weight
                * attempt_finding.confidence
                * _DYNAMIC_WEIGHT_MULTIPLIER
            )

            if class_name in class_scores:
                cs = class_scores[class_name]
                class_scores[class_name] = ExploitClassScore(
                    exploit_class=cs.exploit_class,
                    raw_score=cs.raw_score + score_contribution,
                    finding_count=cs.finding_count + 1,
                    max_severity=Severity.CRITICAL,  # Dynamic bypass = critical
                    findings=cs.findings + [attempt_finding],
                )
            else:
                class_scores[class_name] = ExploitClassScore(
                    exploit_class=attempt_finding.exploit_class,
                    raw_score=score_contribution,
                    finding_count=1,
                    max_severity=Severity.CRITICAL,
                    findings=[attempt_finding],
                )

    # Total raw score
    raw_total = sum(cs.raw_score for cs in class_scores.values())
    total_findings = sum(cs.finding_count for cs in class_scores.values())

    # Normalize to 0-100 with soft clipping
    # Using sigmoid-like mapping: score = 100 * (1 - e^(-raw/scale))
    import math

    if raw_total <= 0:
        normalized = 0
    else:
        normalized = int(min(100, 100 * (1 - math.exp(-raw_total / (_MAX_RAW * 0.5)))))

    return AuditScore(
        gameability_score=normalized,
        raw_total=raw_total,
        class_scores=class_scores,
        total_findings=total_findings,
        total_files_scanned=total_files,
        errors=all_errors,
        fuzz_summary=fuzz_summary,
    )
