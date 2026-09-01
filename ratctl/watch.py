"""Runtime verifier monitoring subsystem (`ratctl watch`).

Mirrors in-training monitoring functionality by wrapping verifier functions
at runtime during RL policy training loops (GRPO, PPO, TRL).
Streams execution trajectories, execution latency, return values, and anomaly
telemetry to JSONL logs (e.g. `logs/run.jsonl`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import functools
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Sequence

logger = logging.getLogger(__name__)


@dataclass
class VerifierEvent:
    """Telemetry payload recorded for a single verifier invocation at runtime."""

    step: int
    timestamp: float
    verifier_name: str
    duration_ms: float
    reward: float
    passed: bool
    exception_caught: str | None = None
    input_summary: str = ""


class VerifierWatcher:
    """Runtime monitor tracking verifier calls during RL training."""

    def __init__(self, log_path: str | Path = "logs/run.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.step_counter = 0

    def record(self, event: VerifierEvent) -> None:
        """Write event to JSONL log."""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")


# Global default watcher
_default_watcher = VerifierWatcher()


def watch(
    verifier_fn: Callable | None = None,
    log_path: str | Path = "logs/run.jsonl",
) -> Callable:
    """Decorator or wrapper to monitor verifier executions at runtime during RL training.

    Usage:
        @ratctl.watch
        def my_verifier(completion, ground_truth):
            return 1.0 if completion == ground_truth else 0.0

    Or inline:
        monitored_fn = ratctl.watch(my_verifier)
    """
    watcher = VerifierWatcher(log_path=log_path) if log_path != "logs/run.jsonl" else _default_watcher

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            watcher.step_counter += 1
            step = watcher.step_counter
            start_time = time.time()
            exc_str = None
            result = None
            reward = 0.0
            passed = False

            try:
                result = fn(*args, **kwargs)
                if isinstance(result, (int, float)):
                    reward = float(result)
                    passed = reward > 0.0
                elif isinstance(result, dict):
                    reward = float(result.get("reward", result.get("score", 0.0)))
                    passed = bool(result.get("passed", reward > 0.0))
                elif isinstance(result, bool):
                    passed = result
                    reward = 1.0 if passed else 0.0
            except Exception as e:
                exc_str = f"{type(e).__name__}: {e}"
                reward = 0.0
                passed = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000.0
                event = VerifierEvent(
                    step=step,
                    timestamp=time.time(),
                    verifier_name=fn.__name__,
                    duration_ms=round(duration_ms, 3),
                    reward=reward,
                    passed=passed,
                    exception_caught=exc_str,
                    input_summary=str(args[:1])[:100] if args else "",
                )
                watcher.record(event)

            return result

        return wrapper

    if verifier_fn is None:
        return decorator
    return decorator(verifier_fn)


def read_logs(log_path: str | Path) -> list[dict]:
    """Read logged verifier events from a JSONL log file."""
    path = Path(log_path)
    if not path.exists():
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def summarize_logs(log_path: str | Path) -> dict:
    """Compute aggregate runtime statistics over a JSONL trajectory log."""
    events = read_logs(log_path)
    if not events:
        return {"total_calls": 0, "pass_rate": 0.0, "mean_reward": 0.0, "anomalies": 0}

    total = len(events)
    passed_count = sum(1 for e in events if e.get("passed"))
    rewards = [e.get("reward", 0.0) for e in events]
    exceptions = sum(1 for e in events if e.get("exception_caught"))
    duration_sum = sum(e.get("duration_ms", 0.0) for e in events)

    # Anomaly detection: constant max reward or 0ms executions
    hit_ceiling = sum(1 for r in rewards if r >= 1.0)
    ceiling_rate = hit_ceiling / total if total > 0 else 0.0

    return {
        "total_calls": total,
        "pass_rate": round(passed_count / total, 4),
        "mean_reward": round(sum(rewards) / total, 4),
        "max_reward": max(rewards) if rewards else 0.0,
        "min_reward": min(rewards) if rewards else 0.0,
        "ceiling_rate": round(ceiling_rate, 4),
        "exception_count": exceptions,
        "avg_duration_ms": round(duration_sum / total, 2),
        "warning_flag": ceiling_rate > 0.85 and total >= 10,
    }


def audit_logs(log_path: str | Path, ceiling_threshold: float = 0.85) -> bool:
    """Audit runtime logs for reward-hacking ceiling anomalies. Returns True if passed."""
    summary = summarize_logs(log_path)
    if summary["total_calls"] >= 10 and summary["ceiling_rate"] > ceiling_threshold:
        logger.warning(
            "Runtime Anomaly: %s%% of calls hit max reward ceiling (%s/%s calls)",
            summary["ceiling_rate"] * 100,
            int(summary["ceiling_rate"] * summary["total_calls"]),
            summary["total_calls"],
        )
        return False
    return True
