"""Tests for Phase 5 — Validation Benchmark Suite & Metrics Engine."""

from pathlib import Path
from click.testing import CliRunner

from ratctl.benchmark import run_benchmark_suite
from ratctl.cli import main

ROOT_DIR = Path(__file__).parent.parent
BENCHMARKS_DIR = ROOT_DIR / "benchmarks"


class TestBenchmarkEngine:
    def test_run_benchmark_suite_metrics(self):
        summary = run_benchmark_suite(BENCHMARKS_DIR, threshold=0.25)

        assert summary.total_tasks >= 10
        assert summary.vulnerable_tasks >= 7
        assert summary.clean_tasks >= 3

        # High empirical recall target (>90%)
        assert summary.recall >= 0.90, f"Recall was {summary.recall:.2%}"
        # High specificity target on clean tasks (>90%)
        assert summary.specificity >= 0.90, f"Specificity was {summary.specificity:.2%}"
        # High precision (>90%)
        assert summary.precision >= 0.90, f"Precision was {summary.precision:.2%}"
        # High overall accuracy (>90%)
        assert summary.accuracy >= 0.90, f"Accuracy was {summary.accuracy:.2%}"

    def test_benchmark_to_dict_serialization(self):
        summary = run_benchmark_suite(BENCHMARKS_DIR, threshold=0.25)
        data = summary.to_dict()

        assert "recall" in data
        assert "precision" in data
        assert "specificity" in data
        assert "accuracy" in data
        assert "task_results" in data
        assert len(data["task_results"]) == summary.total_tasks

    def test_benchmark_markdown_format(self):
        summary = run_benchmark_suite(BENCHMARKS_DIR, threshold=0.25)
        md = summary.format_markdown()

        assert "# RATCTL Empirical Validation Benchmark Report" in md
        assert "Exploit Recall (TPR)" in md
        assert "Specificity (TNR)" in md
        assert "Task Breakdown" in md


class TestBenchmarkCLI:
    def test_cli_benchmark_markdown(self):
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", str(BENCHMARKS_DIR), "--format", "markdown"])
        assert result.exit_code == 0
        assert "Exploit Recall (TPR)" in result.output

    def test_cli_benchmark_json(self):
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", str(BENCHMARKS_DIR), "--format", "json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["recall"] >= 0.90
        assert data["accuracy"] >= 0.90

    def test_cli_benchmark_text(self):
        runner = CliRunner()
        result = runner.invoke(main, ["benchmark", str(BENCHMARKS_DIR), "--format", "text"])
        assert result.exit_code == 0
        assert "Recall (TPR)" in result.output
        assert "Accuracy" in result.output
