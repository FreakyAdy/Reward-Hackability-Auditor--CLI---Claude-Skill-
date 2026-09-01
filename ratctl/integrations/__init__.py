"""Integrations subsystem for TRL, GRPO, and PyTorch RL training loops."""

from __future__ import annotations

from typing import Any, Callable
from ratctl.watch import watch


class GRPOSpy:
    """Wrapper for HuggingFace TRL GRPOTrainer reward functions.

    Monitors multi-reward function arrays during Group Relative Policy Optimization (GRPO).

    Usage:
        from ratctl.integrations import GRPOSpy

        spy = GRPOSpy(reward_funcs=[accuracy_reward, format_reward])
        trainer = GRPOTrainer(
            model=model,
            reward_funcs=spy.wrapped_reward_funcs,
            ...
        )
    """

    def __init__(
        self,
        reward_funcs: list[Callable],
        log_path: str = "logs/grpo_run.jsonl",
    ):
        self.log_path = log_path
        self.original_funcs = reward_funcs
        self.wrapped_reward_funcs = [
            watch(fn, log_path=self.log_path) for fn in reward_funcs
        ]


def watch_trl(reward_funcs: list[Callable], log_path: str = "logs/trl_run.jsonl") -> list[Callable]:
    """Helper function to wrap TRL reward functions for live monitoring."""
    return [watch(fn, log_path=log_path) for fn in reward_funcs]
