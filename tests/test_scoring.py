"""Tests for the scoring engine."""

import pytest

from ratctl.detectors.base import DetectorResult, ExploitClass, Finding, Severity
from ratctl.scoring import score_results


def _make_finding(
    exploit_class: ExploitClass = ExploitClass.TEST_TAMPERING,
    severity: Severity = Severity.HIGH,
) -> Finding:
    return Finding(
        exploit_class=exploit_class,
        severity=severity,
        file_path="test.py",
        line_number=1,
        title="Test finding",
        description="Test description",
        evidence="test evidence",
        suggested_fix="test fix",
        detector_name="test",
    )


class TestScoring:
    def test_empty_results_score_zero(self):
        score = score_results([])
        assert score.gameability_score == 0
        assert score.total_findings == 0

    def test_no_findings_score_zero(self):
        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                files_scanned=5,
            )
        ]
        score = score_results(results)
        assert score.gameability_score == 0

    def test_critical_finding_high_score(self):
        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                findings=[
                    _make_finding(severity=Severity.CRITICAL),
                    _make_finding(severity=Severity.CRITICAL),
                    _make_finding(severity=Severity.CRITICAL),
                ],
                files_scanned=3,
            )
        ]
        score = score_results(results)
        assert score.gameability_score > 30  # Multiple criticals should be significant

    def test_info_finding_low_score(self):
        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.LLM_JUDGE_BIAS,
                findings=[_make_finding(ExploitClass.LLM_JUDGE_BIAS, Severity.INFO)],
                files_scanned=1,
            )
        ]
        score = score_results(results)
        assert score.gameability_score < 10

    def test_threshold_check(self):
        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                findings=[
                    _make_finding(severity=Severity.CRITICAL)
                    for _ in range(5)
                ],
                files_scanned=5,
            )
        ]
        score = score_results(results)
        assert score.exceeds_threshold(0.1)  # Should exceed 10%

    def test_score_breakdown_by_class(self):
        results = [
            DetectorResult(
                detector_name="d1",
                exploit_class=ExploitClass.TEST_TAMPERING,
                findings=[_make_finding(ExploitClass.TEST_TAMPERING, Severity.HIGH)],
            ),
            DetectorResult(
                detector_name="d2",
                exploit_class=ExploitClass.ENV_HIJACKING,
                findings=[_make_finding(ExploitClass.ENV_HIJACKING, Severity.MEDIUM)],
            ),
        ]
        score = score_results(results)
        assert "test_tampering" in score.class_scores
        assert "env_hijacking" in score.class_scores
        assert score.total_findings == 2

    def test_serialization(self):
        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                findings=[_make_finding()],
                files_scanned=1,
            )
        ]
        score = score_results(results)
        data = score.to_dict()
        assert "gameability_score" in data
        assert "class_scores" in data
        assert isinstance(data["gameability_score"], int)
