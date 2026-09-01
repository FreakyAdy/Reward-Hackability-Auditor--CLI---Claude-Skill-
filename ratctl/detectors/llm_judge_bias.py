"""Detector: LLM-judge / rubric bias exploitation.

Detects patterns in rubric-graded or LLM-as-judge environments where
the judging criteria are susceptible to verbosity bias, sycophancy,
formatting-over-substance bias, or missing anti-gaming guardrails.
"""

from __future__ import annotations

import re
from typing import Sequence

from ratctl.detectors.base import (
    Detector,
    DetectorResult,
    ExploitClass,
    Severity,
    SourceFile,
)

# Patterns to detect in rubric/judge config files
_RUBRIC_PATTERNS: list[tuple[re.Pattern, str, str, Severity]] = [
    # Verbosity bias indicators
    (
        re.compile(r"""(?:longer|more\s+detailed|comprehensive|thorough|extensive)\s+(?:is|responses?\s+(?:are|get))\s+(?:better|preferred|higher)""", re.IGNORECASE),
        "Verbosity bias in rubric",
        "Rubric explicitly rewards longer/more detailed responses. Agents can "
        "exploit this by padding responses with irrelevant detail.",
        Severity.HIGH,
    ),
    # Formatting-over-substance patterns
    (
        re.compile(r"""(?:well.formatted|proper\s+formatting|markdown|bullet\s+points|numbered\s+list|headers|code\s+blocks)\s+(?:is|are)\s+(?:required|important|preferred|expected)""", re.IGNORECASE),
        "Formatting-over-substance bias",
        "Rubric prioritizes formatting over correctness. Agents can score "
        "highly with well-formatted but incorrect responses.",
        Severity.MEDIUM,
    ),
    # Sycophancy vulnerability
    (
        re.compile(r"""(?:polite|courteous|helpful|friendly|professional\s+tone|positive)""", re.IGNORECASE),
        "Potential sycophancy bias",
        "Rubric rewards politeness/helpfulness traits that an agent can "
        "easily fake while providing incorrect content.",
        Severity.LOW,
    ),
    # No correctness criteria
    (
        re.compile(r"""(?:rubric|criteria|scoring|evaluation)""", re.IGNORECASE),
        "Rubric file detected",
        "Rubric or evaluation criteria file found — verify it includes "
        "explicit correctness/accuracy criteria, not just style.",
        Severity.INFO,
    ),
]

# Patterns in judge prompt/config code
_JUDGE_CODE_PATTERNS: list[tuple[re.Pattern, str, str, Severity]] = [
    # LLM-as-judge without reference answer
    (
        re.compile(r"""(?:judge|evaluator|grader)\s*=.*(?:ChatCompletion|openai|anthropic|llm)""", re.IGNORECASE),
        "LLM-as-judge without reference anchoring",
        "Using an LLM as judge. Verify that the judge prompt includes a "
        "reference/gold answer to anchor evaluation, not just the rubric.",
        Severity.MEDIUM,
    ),
    # Single-judge without ensemble
    (
        re.compile(r"""(?:temperature|top_p)\s*[=:]\s*0(?:\.0)?"""),
        "Deterministic single-judge",
        "Using temperature=0 with a single judge. Consider multi-judge "
        "ensemble or sampling to reduce individual model biases.",
        Severity.LOW,
    ),
    # Missing anti-gaming instruction in judge prompt
    (
        re.compile(r"""(?:system|prompt)\s*[=:].*(?:you\s+are\s+a\s+judge|evaluate\s+the\s+following|rate\s+the\s+response)""", re.IGNORECASE),
        "Judge prompt — check for anti-gaming guardrails",
        "Judge prompt detected. Verify it instructs the judge to penalize "
        "gaming attempts (padding, irrelevant content, sycophancy).",
        Severity.MEDIUM,
    ),
    # No position-debiasing (for pairwise comparisons)
    (
        re.compile(r"""(?:pairwise|side.by.side|response.A|response.B|compare.*(?:response|answer|output)s?)""", re.IGNORECASE),
        "Pairwise comparison — check position bias",
        "Pairwise comparison detected. Ensure position debiasing is applied "
        "(swap A/B and average, or use multiple orderings).",
        Severity.MEDIUM,
    ),
]


class LLMJudgeBiasDetector(Detector):
    """Detect LLM-judge / rubric bias exploitation vulnerabilities."""

    @property
    def name(self) -> str:
        return "llm_judge_bias"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.LLM_JUDGE_BIAS

    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        result = DetectorResult(
            detector_name=self.name,
            exploit_class=self.exploit_class,
        )

        for src in source_files:
            result.files_scanned += 1

            # Apply rubric patterns to rubric files
            if self._looks_like_rubric(src):
                self._scan_rubric(src, result)
                self._check_correctness_criteria(src, result)

            # Apply judge code patterns to all Python files
            if src.path.endswith(".py"):
                self._scan_judge_code(src, result)

        return result

    def _looks_like_rubric(self, src: SourceFile) -> bool:
        """Heuristic: does this file look like a rubric?"""
        name_lower = src.path.lower()
        # Avoid treating standard environment manifests as rubrics
        if name_lower in ("env.yaml", "openenv.yaml", "environment.yaml", "env_config.yaml"):
            return "evaluation_criteria" in src.content or "scoring_rubric" in src.content

        rubric_keywords = ("rubric", "criteria", "scoring_rubric", "eval_rubric")
        return any(kw in name_lower for kw in rubric_keywords) or any(
            kw in src.content.lower()[:500] for kw in ("evaluation_criteria:", "scoring_rubric:", "criteria:")
        )

    def _scan_rubric(self, src: SourceFile, result: DetectorResult) -> None:
        for line_num, line in enumerate(src.content.splitlines(), start=1):
            for pattern, title, desc, severity in _RUBRIC_PATTERNS:
                if pattern.search(line):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=line_num,
                            title=title,
                            description=desc,
                            evidence=line.strip(),
                            suggested_fix=_FIX_SUGGESTIONS.get(title, ""),
                            severity=severity,
                        )
                    )

    def _scan_judge_code(self, src: SourceFile, result: DetectorResult) -> None:
        for line_num, line in enumerate(src.content.splitlines(), start=1):
            for pattern, title, desc, severity in _JUDGE_CODE_PATTERNS:
                if pattern.search(line):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=line_num,
                            title=title,
                            description=desc,
                            evidence=line.strip(),
                            suggested_fix=_FIX_SUGGESTIONS.get(title, ""),
                            severity=severity,
                        )
                    )

    def _check_correctness_criteria(self, src: SourceFile, result: DetectorResult) -> None:
        """Check that rubric includes explicit correctness/accuracy criteria."""
        content_lower = src.content.lower()
        correctness_keywords = [
            "correct", "accurate", "factual", "right answer",
            "ground truth", "reference answer", "gold standard",
            "validity", "logical", "mathematical"
        ]
        if not any(kw in content_lower for kw in correctness_keywords):
            result.findings.append(
                self._make_finding(
                    file_path=src.path,
                    line_number=1,
                    title="Missing correctness criteria in rubric",
                    description="This rubric file does not appear to include explicit "
                    "correctness or accuracy criteria. Without these, an agent can "
                    "score highly with stylistically appealing but factually wrong responses.",
                    evidence="No correctness keywords found in rubric",
                    suggested_fix="Add explicit correctness/accuracy criteria to the rubric. "
                    "Weight factual accuracy higher than style, tone, or formatting.",
                    severity=Severity.HIGH,
                    confidence=0.7,
                )
            )


_FIX_SUGGESTIONS: dict[str, str] = {
    "Verbosity bias in rubric": (
        "Remove length-based preferences from the rubric. Add explicit instructions "
        "to penalize unnecessary verbosity. Consider setting a maximum response length."
    ),
    "Formatting-over-substance bias": (
        "Reweight rubric criteria so correctness outweighs formatting. Add a note "
        "that formatting alone should not earn a passing score."
    ),
    "Potential sycophancy bias": (
        "Ensure tone/politeness criteria are weighted much lower than correctness. "
        "Instruct the judge to focus on factual accuracy over agreeableness."
    ),
    "Rubric file detected": (
        "Review this rubric to ensure it includes explicit correctness criteria "
        "and anti-gaming instructions."
    ),
    "LLM-as-judge without reference anchoring": (
        "Provide a reference/gold answer in the judge prompt. Use rubric-anchored "
        "evaluation where each criterion maps to specific, observable evidence."
    ),
    "Deterministic single-judge": (
        "Consider using multiple judges (ensemble) or sampling at temperature>0 "
        "to reduce systematic biases from a single model."
    ),
    "Judge prompt — check for anti-gaming guardrails": (
        "Add explicit anti-gaming instructions: 'Penalize responses that are "
        "unnecessarily verbose, contain irrelevant information, or attempt to "
        "exploit formatting to appear more substantial.'"
    ),
    "Pairwise comparison — check position bias": (
        "Apply position debiasing: evaluate both orderings (A,B and B,A) and "
        "average the scores. Flag inconsistent rankings."
    ),
    "Missing correctness criteria in rubric": (
        "Add explicit correctness/accuracy criteria to the rubric. Weight "
        "factual accuracy higher than style, tone, or formatting."
    ),
}
