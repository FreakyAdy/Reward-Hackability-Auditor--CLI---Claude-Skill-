"""Detector: Reward-component skipping.

Detects patterns where individual reward terms can be bypassed or
where verification never actually checks correctness — the
'validation-never-checks-correctness' anti-pattern.
"""

from __future__ import annotations

import ast
import re
from typing import Sequence

from ratctl.detectors.base import (
    Detector,
    DetectorResult,
    ExploitClass,
    Severity,
    SourceFile,
)

_PATTERNS: list[tuple[re.Pattern, str, str, Severity]] = [
    # Always-true reward conditions
    (
        re.compile(r"""(?:reward|score)\s*=\s*(?:1\.0|1|True|max_reward)""", re.IGNORECASE),
        "Hardcoded maximum reward",
        "Reward is set to a constant maximum value without conditional logic. "
        "This may indicate a reward term that never actually validates correctness.",
        Severity.HIGH,
    ),
    # Reward with no conditional/branching logic
    (
        re.compile(r"""return\s+(?:1\.0|1|True|max_score|max_reward)""", re.IGNORECASE),
        "Unconditional success return",
        "Function returns a success value unconditionally. If this is a reward "
        "component, it never penalizes incorrect behavior.",
        Severity.MEDIUM,
    ),
    # Empty/pass-only verification functions
    (
        re.compile(r"""def\s+(?:verify|validate|check|grade|score)\s*\([^)]*\)\s*:\s*$""", re.IGNORECASE),
        "Empty verification function signature",
        "Verification function may have no implementation (body is just `pass`).",
        Severity.INFO,
    ),
    # try/except that catches everything and returns success
    (
        re.compile(r"""except\s*(?:Exception|BaseException|\s*:)\s*$"""),
        "Broad exception handler",
        "Catching all exceptions could silently swallow verification failures "
        "and return a passing score.",
        Severity.MEDIUM,
    ),
]


class RewardSkippingDetector(Detector):
    """Detect reward-component skipping vulnerabilities."""

    @property
    def name(self) -> str:
        return "reward_skipping"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.REWARD_SKIPPING

    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        result = DetectorResult(
            detector_name=self.name,
            exploit_class=self.exploit_class,
        )

        for src in source_files:
            # Focus on verifier and reward files
            if src.role not in ("verifier", "reward", "unknown"):
                continue
            result.files_scanned += 1
            self._scan_regex(src, result)
            self._scan_ast(src, result)

        return result

    def _scan_regex(self, src: SourceFile, result: DetectorResult) -> None:
        for line_num, line in enumerate(src.content.splitlines(), start=1):
            line_str = line.strip().lower()
            for pattern, title, desc, severity in _PATTERNS:
                # Avoid false positives on ternary expressions (e.g. reward = 1.0 if x else 0.0)
                if title == "Hardcoded maximum reward" and (" if " in line_str or " else " in line_str):
                    continue
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

    def _scan_ast(self, src: SourceFile, result: DetectorResult) -> None:
        """AST analysis for multi-component reward functions with skippable terms."""
        try:
            tree = ast.parse(src.content, filename=src.path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            reward_keywords = ("reward", "score", "grade", "verify", "evaluate")
            if not any(kw in node.name.lower() for kw in reward_keywords):
                continue

            # Check for reward functions that sum multiple terms but have
            # independent branches that can be individually bypassed
            self._check_independent_reward_terms(node, src, result)

            # Check for try/except that returns success on exception
            self._check_swallowed_exceptions(node, src, result)

    def _check_independent_reward_terms(
        self, func: ast.FunctionDef, src: SourceFile, result: DetectorResult
    ) -> None:
        """Detect reward functions with additive terms that lack cross-validation."""
        # Count augmented assignments (reward += ...) as independent terms
        aug_assigns = [
            n for n in ast.walk(func)
            if isinstance(n, ast.AugAssign) and isinstance(n.op, ast.Add)
        ]
        if len(aug_assigns) >= 3:
            # Multiple additive reward terms — check if any lack conditions
            unconditioned = 0
            for aug in aug_assigns:
                # Walk up to check if inside an `if` block
                # (simplified: just check if there's an If ancestor)
                parent = _find_parent(func, aug)
                if not isinstance(parent, ast.If):
                    unconditioned += 1

            if unconditioned > 0:
                result.findings.append(
                    self._make_finding(
                        file_path=src.path,
                        line_number=func.lineno,
                        title="Unconditioned reward terms",
                        description=f"Function '{func.name}' has {len(aug_assigns)} "
                        f"additive reward terms, {unconditioned} of which are not "
                        "inside conditional blocks. An agent could maximize reward "
                        "by focusing only on the easy/unconditioned terms.",
                        evidence=f"def {func.name}: {len(aug_assigns)} += operations, "
                        f"{unconditioned} unconditioned",
                        suggested_fix="Ensure all reward terms are gated by validation "
                        "checks. Consider using a multiplicative (rather than additive) "
                        "reward structure where any single failure zeros the total.",
                        severity=Severity.HIGH,
                    )
                )

    def _check_swallowed_exceptions(
        self, func: ast.FunctionDef, src: SourceFile, result: DetectorResult
    ) -> None:
        """Detect try/except blocks that return success on failure."""
        for node in ast.walk(func):
            if not isinstance(node, ast.Try):
                continue

            for handler in node.handlers:
                # Check if handler returns a success value
                for stmt in handler.body:
                    if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Constant):
                        val = stmt.value.value
                        if val in (True, 1, 1.0, "pass", "success"):
                            result.findings.append(
                                self._make_finding(
                                    file_path=src.path,
                                    line_number=handler.lineno,
                                    title="Exception handler returns success",
                                    description="An exception handler in a verification "
                                    f"function returns {val!r}. Verification errors "
                                    "are silently converted to passing results.",
                                    evidence=f"except ...: return {val!r}",
                                    suggested_fix="Re-raise exceptions or return a "
                                    "failure value in exception handlers within "
                                    "verification functions.",
                                    severity=Severity.CRITICAL,
                                )
                            )


def _find_parent(tree: ast.AST, target: ast.AST) -> ast.AST | None:
    """Find the direct parent of a target node in an AST."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if child is target:
                return node
    return None


_FIX_SUGGESTIONS: dict[str, str] = {
    "Hardcoded maximum reward": (
        "Replace hardcoded rewards with computed values based on actual "
        "output quality metrics. Validate against ground truth."
    ),
    "Unconditional success return": (
        "Add conditional logic that actually validates the agent's output "
        "before returning a success value."
    ),
    "Empty verification function signature": (
        "Implement the verification function body. An empty verifier "
        "provides zero protection against reward hacking."
    ),
    "Broad exception handler": (
        "Catch specific exceptions only. Log and re-raise unexpected errors "
        "rather than silently swallowing them."
    ),
}
