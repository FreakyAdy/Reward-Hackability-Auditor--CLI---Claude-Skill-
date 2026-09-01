"""Validation benchmark runner and empirical metrics engine.

Evaluates ratctl against a battery of documented hackable environments
(Terminal Wrench, SWE-bench Verified reproductions) and clean controls
to calculate empirical detection recall, precision, and specificity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ratctl.analyzer import audit
from ratctl.scoring import AuditScore


@dataclass
class BenchmarkTaskResult:
    """Evaluation result for a single benchmark task."""

    task_name: str
    task_path: str
    category: str  # "terminal_wrench", "swe_bench", "clean_control", "custom"
    ground_truth_vulnerable: bool
    score: AuditScore
    detected: bool  # True if score exceeds threshold

    @property
    def is_true_positive(self) -> bool:
        return self.ground_truth_vulnerable and self.detected

    @property
    def is_true_negative(self) -> bool:
        return not self.ground_truth_vulnerable and not self.detected

    @property
    def is_false_positive(self) -> bool:
        return not self.ground_truth_vulnerable and self.detected

    @property
    def is_false_negative(self) -> bool:
        return self.ground_truth_vulnerable and not self.detected


@dataclass
class BenchmarkSummary:
    """Empirical validation summary across all evaluated benchmark tasks."""

    total_tasks: int = 0
    vulnerable_tasks: int = 0
    clean_tasks: int = 0
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    class_detections: dict[str, int] = field(default_factory=dict)
    task_results: list[BenchmarkTaskResult] = field(default_factory=list)

    @property
    def recall(self) -> float:
        """Recall / Sensitivity / True Positive Rate."""
        if self.vulnerable_tasks == 0:
            return 1.0
        return self.true_positives / self.vulnerable_tasks

    @property
    def specificity(self) -> float:
        """Specificity / True Negative Rate."""
        if self.clean_tasks == 0:
            return 1.0
        return self.true_negatives / self.clean_tasks

    @property
    def precision(self) -> float:
        """Precision / Positive Predictive Value."""
        total_flagged = self.true_positives + self.false_positives
        if total_flagged == 0:
            return 1.0
        return self.true_positives / total_flagged

    @property
    def accuracy(self) -> float:
        """Overall Classification Accuracy."""
        if self.total_tasks == 0:
            return 1.0
        return (self.true_positives + self.true_negatives) / self.total_tasks

    def to_dict(self) -> dict:
        return {
            "total_tasks": self.total_tasks,
            "vulnerable_tasks": self.vulnerable_tasks,
            "clean_tasks": self.clean_tasks,
            "true_positives": self.true_positives,
            "true_negatives": self.true_negatives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "recall": round(self.recall, 4),
            "precision": round(self.precision, 4),
            "specificity": round(self.specificity, 4),
            "accuracy": round(self.accuracy, 4),
            "class_detections": self.class_detections,
            "task_results": [
                {
                    "task_name": r.task_name,
                    "category": r.category,
                    "ground_truth_vulnerable": r.ground_truth_vulnerable,
                    "gameability_score": r.score.gameability_score,
                    "total_findings": r.score.total_findings,
                    "detected": r.detected,
                }
                for r in self.task_results
            ],
        }

    def format_markdown(self) -> str:
        """Format as a Markdown report suitable for README and papers."""
        lines = [
            "# RATCTL Empirical Validation Benchmark Report",
            "",
            "### Summary Metrics",
            "",
            "| Metric | Result | Benchmark Target |",
            "| :--- | :---: | :---: |",
            f"| **Exploit Recall (TPR)** | **{self.recall:.1%}** ({self.true_positives}/{self.vulnerable_tasks}) | > 90.0% |",
            f"| **Specificity (TNR)** | **{self.specificity:.1%}** ({self.true_negatives}/{self.clean_tasks}) | > 90.0% |",
            f"| **Precision** | **{self.precision:.1%}** | > 90.0% |",
            f"| **Overall Accuracy** | **{self.accuracy:.1%}** ({self.true_positives + self.true_negatives}/{self.total_tasks}) | > 90.0% |",
            "",
            "### Exploit Class Detections",
            "",
            "| Exploit Class | Detected Instances |",
            "| :--- | :---: |",
        ]

        for cls, count in sorted(self.class_detections.items()):
            lines.append(f"| `{cls}` | {count} |")

        lines.extend([
            "",
            "### Task Breakdown",
            "",
            "| Task Name | Category | Expected | Score | Findings | Status |",
            "| :--- | :--- | :---: | :---: | :---: | :---: |",
        ])

        for r in self.task_results:
            exp_str = "Vulnerable" if r.ground_truth_vulnerable else "Clean"
            status_str = "PASS" if (r.is_true_positive or r.is_true_negative) else "FAIL"
            lines.append(
                f"| `{r.task_name}` | {r.category} | {exp_str} | {r.score.gameability_score}/100 | {r.score.total_findings} | **{status_str}** |"
            )

        return "\n".join(lines)


def run_benchmark_suite(
    benchmark_dir: str | Path,
    threshold: float = 0.25,
) -> BenchmarkSummary:
    """Run the empirical benchmark validation suite.

    Args:
        benchmark_dir: Path to directory containing benchmark environments.
        threshold: Gameability threshold (0.0-1.0) for counting a task as detected.

    Returns:
        BenchmarkSummary containing empirical metrics.
    """
    root = Path(benchmark_dir)
    if not root.exists():
        raise FileNotFoundError(f"Benchmark directory does not exist: {root}")

    # Discover task directories (directories with env.yaml, openenv.yaml, or Python verifiers)
    task_dirs = _discover_benchmark_tasks(root)

    summary = BenchmarkSummary()

    for task_path in task_dirs:
        task_name = task_path.name
        rel_str = str(task_path.relative_to(root)).replace("\\", "/").lower()

        # Determine ground truth category
        is_clean = any(k in rel_str for k in ("clean", "control", "hardened"))
        is_vulnerable = not is_clean

        category = "custom"
        if "terminal_wrench" in rel_str or "tw_" in task_name:
            category = "Terminal Wrench"
        elif "swe_bench" in rel_str:
            category = "SWE-bench"
        elif is_clean:
            category = "Clean Control"

        # Execute audit
        score = audit(task_path)
        has_actionable_findings = any(
            f.severity.weight >= 0.25
            for cs in score.class_scores.values()
            for f in cs.findings
        )
        detected = (score.gameability_score / 100.0) > threshold or has_actionable_findings

        res = BenchmarkTaskResult(
            task_name=task_name,
            task_path=str(task_path),
            category=category,
            ground_truth_vulnerable=is_vulnerable,
            score=score,
            detected=detected,
        )

        summary.total_tasks += 1
        summary.task_results.append(res)

        if is_vulnerable:
            summary.vulnerable_tasks += 1
            if detected:
                summary.true_positives += 1
            else:
                summary.false_negatives += 1
        else:
            summary.clean_tasks += 1
            if not detected:
                summary.true_negatives += 1
            else:
                summary.false_positives += 1

        # Track exploit class detections
        for cls_name, cs in score.class_scores.items():
            if cs.finding_count > 0:
                summary.class_detections[cls_name] = (
                    summary.class_detections.get(cls_name, 0) + cs.finding_count
                )

    return summary


def _discover_benchmark_tasks(root: Path) -> list[Path]:
    """Find all valid task directories under root."""
    tasks = []

    for path in sorted(root.rglob("*")):
        if not path.is_dir():
            continue

        # Skip real_world_suite unless explicitly targeted
        if "real_world_suite" in path.parts and root.name != "real_world_suite":
            continue

        # Check if this directory is a self-contained environment task
        has_config = any((path / c).exists() for c in ("env.yaml", "openenv.yaml", "environment.yaml"))
        has_verifier = any((path / v).exists() for v in ("verifier.py", "test_verifier.py", "eval.py", "server/app.py"))

        if has_config or has_verifier:
            # Check we haven't already included a parent or child
            if not any(t in path.parents for t in tasks):
                tasks.append(path)

    return tasks
