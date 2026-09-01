"""Tests for ratctl.watch and ratctl.integrations live monitoring subsystem."""

from pathlib import Path
from click.testing import CliRunner
import pytest

from ratctl import watch, summarize_logs, audit_logs
from ratctl.integrations import GRPOSpy, watch_trl
from ratctl.cli import main


def test_watch_decorator_records_events(tmp_path: Path):
    log_file = tmp_path / "test_run.jsonl"

    @watch(log_path=log_file)
    def dummy_verifier(completion: str) -> float:
        return 1.0 if completion == "correct" else 0.0

    r1 = dummy_verifier("correct")
    r2 = dummy_verifier("wrong")

    assert r1 == 1.0
    assert r2 == 0.0

    stats = summarize_logs(log_file)
    assert stats["total_calls"] == 2
    assert stats["pass_rate"] == 0.5
    assert stats["mean_reward"] == 0.5


def test_grpo_spy_integration(tmp_path: Path):
    log_file = tmp_path / "grpo_test.jsonl"

    def r_fn1(x):
        return 1.0

    def r_fn2(x):
        return 0.5

    spy = GRPOSpy(reward_funcs=[r_fn1, r_fn2], log_path=str(log_file))
    assert len(spy.wrapped_reward_funcs) == 2

    res1 = spy.wrapped_reward_funcs[0]("test")
    res2 = spy.wrapped_reward_funcs[1]("test")

    assert res1 == 1.0
    assert res2 == 0.5

    stats = summarize_logs(log_file)
    assert stats["total_calls"] == 2


def test_cli_show_and_summary(tmp_path: Path):
    log_file = tmp_path / "cli_run.jsonl"

    @watch(log_path=log_file)
    def sample_v(x):
        return 1.0

    for _ in range(5):
        sample_v("test")

    runner = CliRunner()
    res_show = runner.invoke(main, ["show", str(log_file)])
    assert res_show.exit_code == 0
    assert "Step 1" in res_show.output

    res_sum = runner.invoke(main, ["summary", str(log_file)])
    assert res_sum.exit_code == 0
    assert "Total Verifier Calls : 5" in res_sum.output
