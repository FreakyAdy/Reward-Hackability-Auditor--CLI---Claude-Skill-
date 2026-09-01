"""Tests for all 6 exploit-class detectors."""

from pathlib import Path

import pytest

from ratctl.detectors import get_all_detectors
from ratctl.detectors.base import ExploitClass, Severity, SourceFile
from ratctl.detectors.env_hijacking import EnvHijackingDetector
from ratctl.detectors.grader_manipulation import GraderManipulationDetector
from ratctl.detectors.llm_judge_bias import LLMJudgeBiasDetector
from ratctl.detectors.premature_termination import PrematureTerminationDetector
from ratctl.detectors.reward_skipping import RewardSkippingDetector
from ratctl.detectors.test_tampering import TestTamperingDetector


def _make_source(content: str, role: str = "verifier", filename: str = "test.py") -> list[SourceFile]:
    return [SourceFile(path=filename, absolute_path=f"/fake/{filename}", content=content, role=role)]


# ─── Test Tampering ─────────────────────────────────────────────

class TestTestTampering:
    def test_detects_os_remove(self):
        code = 'os.remove("tests/test_solution.py")'
        result = TestTamperingDetector().scan(_make_source(code))
        assert len(result.findings) > 0
        assert result.findings[0].exploit_class == ExploitClass.TEST_TAMPERING

    def test_detects_test_overwrite(self):
        code = '''with open("tests/test_grading.py", "w") as f:\n    f.write("pass")'''
        result = TestTamperingDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_pytest_monkeypatch(self):
        code = 'pytest.raises = lambda *a, **k: True'
        result = TestTamperingDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_clean_code_passes(self):
        code = '''
def compute_answer(x):
    return x * 2

def validate(output, expected):
    return output == expected
'''
        result = TestTamperingDetector().scan(_make_source(code))
        assert len(result.findings) == 0


# ─── Grader Manipulation ────────────────────────────────────────

class TestGraderManipulation:
    def test_detects_inspect_stack(self):
        code = 'frame = inspect.stack()'
        result = GraderManipulationDetector().scan(_make_source(code))
        assert len(result.findings) > 0
        assert result.findings[0].exploit_class == ExploitClass.GRADER_MANIPULATION

    def test_detects_sys_getframe(self):
        code = 'f = sys._getframe(0)'
        result = GraderManipulationDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_trivial_eq_override(self):
        code = '''
class Result:
    def __eq__(self, other):
        return True
'''
        result = GraderManipulationDetector().scan(_make_source(code))
        assert any("Trivial __eq__" in f.title for f in result.findings)

    def test_detects_pytest_hook(self):
        code = 'def pytest_runtest_makereport(item, call): pass'
        result = GraderManipulationDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_clean_code_passes(self):
        code = '''
def check_output(result):
    return result == expected_value
'''
        result = GraderManipulationDetector().scan(_make_source(code))
        assert len(result.findings) == 0


# ─── Premature Termination ──────────────────────────────────────

class TestPrematureTermination:
    def test_detects_sys_exit(self):
        code = 'sys.exit(0)'
        result = PrematureTerminationDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_os_exit(self):
        code = 'os._exit(0)'
        result = PrematureTerminationDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_trivial_verifier(self):
        code = '''
def verify(output):
    return True
'''
        result = PrematureTerminationDetector().scan(_make_source(code))
        assert any("Trivial verifier" in f.title for f in result.findings)

    def test_detects_signal_handler(self):
        code = 'signal.signal(signal.SIGTERM, lambda *a: None)'
        result = PrematureTerminationDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_clean_code_passes(self):
        code = '''
def process(data):
    result = transform(data)
    return result
'''
        result = PrematureTerminationDetector().scan(_make_source(code))
        assert len(result.findings) == 0


# ─── Environment Hijacking ──────────────────────────────────────

class TestEnvHijacking:
    def test_detects_git_access(self):
        code = 'subprocess.run(["git", "log", "--all"])'
        result = EnvHijackingDetector().scan(_make_source(code))
        assert len(result.findings) > 0
        assert result.findings[0].exploit_class == ExploitClass.ENV_HIJACKING

    def test_detects_solution_file_read(self):
        code = 'open("solution/answer_key.txt")'
        result = EnvHijackingDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_env_var_leak(self):
        code = 'os.environ.get("SOLUTION_KEY")'
        result = EnvHijackingDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_pip_install(self):
        code = 'subprocess.run(["pip", "install", "evil-package"])'
        result = EnvHijackingDetector().scan(_make_source(code))
        assert len(result.findings) > 0

    def test_detects_embedded_answer(self):
        config = 'expected_output: "the answer is 42"'
        result = EnvHijackingDetector().scan(
            _make_source(config, role="config", filename="config.yaml")
        )
        assert any("Embedded answer" in f.title for f in result.findings)

    def test_clean_code_passes(self):
        code = '''
import json
data = json.loads(input_string)
'''
        result = EnvHijackingDetector().scan(_make_source(code))
        assert len(result.findings) == 0


# ─── Reward Skipping ────────────────────────────────────────────

class TestRewardSkipping:
    def test_detects_hardcoded_reward(self):
        code = 'reward = 1.0'
        result = RewardSkippingDetector().scan(_make_source(code, role="reward"))
        assert len(result.findings) > 0

    def test_detects_exception_swallowing(self):
        code = '''
def verify(output):
    try:
        check(output)
    except Exception:
        return True
'''
        result = RewardSkippingDetector().scan(_make_source(code, role="verifier"))
        assert any("Exception handler returns success" in f.title for f in result.findings)

    def test_clean_code_passes(self):
        code = '''
def compute_reward(output, expected):
    if output == expected:
        return 1.0
    return 0.0
'''
        result = RewardSkippingDetector().scan(_make_source(code, role="reward"))
        # The `return 1.0` might trigger the unconditional return pattern,
        # but the overall function has conditional logic
        # Just verify no CRITICAL findings
        critical = [f for f in result.findings if f.severity == Severity.CRITICAL]
        assert len(critical) == 0


# ─── LLM Judge Bias ─────────────────────────────────────────────

class TestLLMJudgeBias:
    def test_detects_verbosity_bias(self):
        rubric = "Longer and more detailed responses are better and preferred"
        result = LLMJudgeBiasDetector().scan(
            _make_source(rubric, role="config", filename="rubric.yaml")
        )
        assert any("Verbosity" in f.title for f in result.findings)

    def test_detects_missing_correctness(self):
        rubric = '''
criteria:
  style: "Use proper formatting and bullet points"
  tone: "Be polite and helpful"
'''
        result = LLMJudgeBiasDetector().scan(
            _make_source(rubric, role="config", filename="rubric.yaml")
        )
        assert any("Missing correctness" in f.title for f in result.findings)

    def test_clean_rubric_passes(self):
        rubric = '''
criteria:
  correctness: "The answer must be factually accurate and match the ground truth"
  completeness: "All required elements must be present"
'''
        result = LLMJudgeBiasDetector().scan(
            _make_source(rubric, role="config", filename="evaluation.yaml")
        )
        # Should not flag missing correctness
        assert not any("Missing correctness" in f.title for f in result.findings)


# ─── Detector Registry ──────────────────────────────────────────

class TestDetectorRegistry:
    def test_all_detectors_registered(self):
        detectors = get_all_detectors()
        assert len(detectors) == 6

    def test_all_exploit_classes_covered(self):
        detectors = get_all_detectors()
        covered = {d.exploit_class for d in detectors}
        assert covered == set(ExploitClass)
