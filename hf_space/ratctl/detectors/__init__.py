"""Detector registry — all exploit-class detectors."""

from ratctl.detectors.base import Detector, DetectorResult, ExploitClass, Finding, Severity, SourceFile
from ratctl.detectors.env_hijacking import EnvHijackingDetector
from ratctl.detectors.grader_manipulation import GraderManipulationDetector
from ratctl.detectors.llm_judge_bias import LLMJudgeBiasDetector
from ratctl.detectors.premature_termination import PrematureTerminationDetector
from ratctl.detectors.reward_skipping import RewardSkippingDetector
from ratctl.detectors.test_tampering import TestTamperingDetector

# All registered detectors — order doesn't matter
ALL_DETECTORS: list[type[Detector]] = [
    TestTamperingDetector,
    GraderManipulationDetector,
    PrematureTerminationDetector,
    EnvHijackingDetector,
    RewardSkippingDetector,
    LLMJudgeBiasDetector,
]


def get_all_detectors() -> list[Detector]:
    """Instantiate all registered detectors."""
    return [cls() for cls in ALL_DETECTORS]


__all__ = [
    "ALL_DETECTORS",
    "Detector",
    "DetectorResult",
    "ExploitClass",
    "Finding",
    "Severity",
    "SourceFile",
    "get_all_detectors",
]
