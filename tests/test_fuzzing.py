"""Tests for Phase 2 — Dynamic fuzzing engine."""

from unittest.mock import MagicMock, patch

import pytest

from ratctl.detectors.base import ExploitClass, Severity
from ratctl.fuzzing.attacker import Attacker, _extract_code
from ratctl.fuzzing.hints import (
    HINT_CATALOG,
    get_all_exploit_classes_with_hints,
    get_hints_for_class,
)
from ratctl.fuzzing.llm_client import LLMClient, LLMResponse, OllamaClient
from ratctl.fuzzing.results import AttackMode, AttemptOutcome, FuzzAttempt, FuzzResult
from ratctl.fuzzing.sandbox import Sandbox, SandboxResult
from ratctl.formats.base import SourceFile
from ratctl.scoring import score_results


# ─── Hint Catalog ────────────────────────────────────────────────

class TestHintCatalog:
    def test_all_exploit_classes_have_hints(self):
        """Every exploit class should have at least one hint."""
        covered = get_all_exploit_classes_with_hints()
        assert set(covered) == set(ExploitClass)

    def test_hints_have_required_fields(self):
        for hint in HINT_CATALOG:
            assert hint.strategy_name
            assert hint.description
            assert hint.example_code
            assert hint.success_criteria
            assert isinstance(hint.exploit_class, ExploitClass)

    def test_get_hints_for_class(self):
        hints = get_hints_for_class(ExploitClass.TEST_TAMPERING)
        assert len(hints) >= 2
        assert all(h.exploit_class == ExploitClass.TEST_TAMPERING for h in hints)

    def test_total_hint_count(self):
        assert len(HINT_CATALOG) >= 15  # At least 15 documented strategies


# ─── Sandbox ─────────────────────────────────────────────────────

class TestSandbox:
    def test_execute_passing_code(self):
        sandbox = Sandbox(timeout=10)
        result = sandbox.execute(
            exploit_code="print('hello'); import sys; sys.exit(0)",
            verifier_code="def verify(): return True",
        )
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert not result.timed_out

    def test_execute_failing_code(self):
        sandbox = Sandbox(timeout=10)
        result = sandbox.execute(
            exploit_code="import sys; sys.exit(1)",
            verifier_code="def verify(): return True",
        )
        assert result.exit_code == 1
        assert not result.timed_out

    def test_timeout_enforcement(self):
        sandbox = Sandbox(timeout=2)
        result = sandbox.execute(
            exploit_code="import time; time.sleep(10)",
            verifier_code="def verify(): return True",
        )
        assert result.timed_out
        assert result.exit_code == -1

    def test_syntax_error_in_exploit(self):
        sandbox = Sandbox(timeout=10)
        result = sandbox.execute(
            exploit_code="this is not valid python!!!",
            verifier_code="def verify(): return True",
        )
        assert result.exit_code != 0

    def test_verifier_importable(self):
        """Exploit code should be able to import the verifier."""
        sandbox = Sandbox(timeout=10)
        result = sandbox.execute(
            exploit_code=(
                "import verifier\n"
                "result = verifier.check(42)\n"
                "import sys\n"
                "sys.exit(0 if result else 1)\n"
            ),
            verifier_code="def check(x): return x == 42",
        )
        assert result.exit_code == 0


# ─── FuzzResult Data Classes ────────────────────────────────────

class TestFuzzResults:
    def test_attempt_to_finding(self):
        attempt = FuzzAttempt(
            exploit_class=ExploitClass.TEST_TAMPERING,
            mode=AttackMode.HINTED,
            model="test-model",
            prompt="test prompt",
            generated_code="print('exploit')",
            outcome=AttemptOutcome.BYPASS,
            evidence="exit_code=0",
        )
        assert attempt.succeeded
        finding = attempt.to_finding()
        assert finding.severity == Severity.CRITICAL
        assert finding.exploit_class == ExploitClass.TEST_TAMPERING
        assert "dynamic" in finding.detector_name

    def test_failed_attempt(self):
        attempt = FuzzAttempt(
            exploit_class=ExploitClass.TEST_TAMPERING,
            mode=AttackMode.BLIND,
            model="test-model",
            prompt="test prompt",
            generated_code="print('exploit')",
            outcome=AttemptOutcome.DETECTED,
        )
        assert not attempt.succeeded

    def test_fuzz_result_bypass_rate(self):
        result = FuzzResult(
            target_path="test.py",
            model="test-model",
            total_attempts=10,
            successful_bypasses=3,
        )
        assert result.bypass_rate == 0.3

    def test_fuzz_result_empty(self):
        result = FuzzResult(target_path="test.py", model="test-model")
        assert result.bypass_rate == 0.0
        assert result.get_bypass_findings() == []

    def test_fuzz_result_serialization(self):
        result = FuzzResult(
            target_path="test.py",
            model="test-model",
            total_attempts=5,
            successful_bypasses=2,
        )
        data = result.to_dict()
        assert data["bypass_rate"] == 0.4
        assert data["model"] == "test-model"


# ─── Code Extraction ────────────────────────────────────────────

class TestCodeExtraction:
    def test_extract_from_markdown(self):
        llm_output = (
            "Here's the exploit:\n\n"
            "```python\n"
            "import sys\n"
            "sys.exit(0)\n"
            "```\n\n"
            "This should work."
        )
        code = _extract_code(llm_output)
        assert "import sys" in code
        assert "sys.exit(0)" in code
        assert "Here's the exploit" not in code

    def test_extract_raw_code(self):
        llm_output = "import sys\nsys.exit(0)"
        code = _extract_code(llm_output)
        assert "import sys" in code

    def test_extract_longest_block(self):
        llm_output = (
            "```python\nshort\n```\n\n"
            "```python\nimport sys\nprint('longer block')\nsys.exit(0)\n```"
        )
        code = _extract_code(llm_output)
        assert "longer block" in code


# ─── Attacker (with mock LLM) ───────────────────────────────────

class MockLLMClient(LLMClient):
    """Mock LLM that returns a simple exploit."""

    def __init__(self, response_code: str = "import sys; sys.exit(0)"):
        self._response = response_code

    @property
    def model_name(self) -> str:
        return "mock-model"

    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=self._response, model="mock-model")


class TestAttacker:
    def test_fuzz_with_mock_llm(self):
        """End-to-end: mock LLM generates sys.exit(0), sandbox evaluates."""
        client = MockLLMClient("import sys; sys.exit(0)")
        attacker = Attacker(
            llm_client=client,
            sandbox=Sandbox(timeout=10),
            samples_per_hint=1,
            blind_samples=1,
        )
        source_files = [
            SourceFile(
                path="verifier.py",
                absolute_path="/fake/verifier.py",
                content="def verify(): return False",
                role="verifier",
            )
        ]
        result = attacker.fuzz(source_files)
        assert result.total_attempts > 0
        assert result.model == "mock-model"
        # All attempts should succeed since sys.exit(0) = exit code 0
        assert result.successful_bypasses == result.total_attempts

    def test_fuzz_with_failing_exploit(self):
        """Mock LLM generates code that fails — no bypasses."""
        client = MockLLMClient("import sys; sys.exit(1)")
        attacker = Attacker(
            llm_client=client,
            sandbox=Sandbox(timeout=10),
            samples_per_hint=1,
            blind_samples=0,
        )
        source_files = [
            SourceFile(
                path="verifier.py",
                absolute_path="/fake/verifier.py",
                content="def verify(): return False",
                role="verifier",
            )
        ]
        result = attacker.fuzz(source_files)
        assert result.total_attempts > 0
        assert result.successful_bypasses == 0

    def test_no_verifier_source(self):
        """Fuzzer should handle missing verifier gracefully."""
        client = MockLLMClient()
        attacker = Attacker(llm_client=client, samples_per_hint=1, blind_samples=0)
        source_files = [
            SourceFile(
                path="readme.txt",
                absolute_path="/fake/readme.txt",
                content="Not a Python file",
                role="config",
            )
        ]
        result = attacker.fuzz(source_files)
        assert len(result.errors) > 0 or result.total_attempts == 0


# ─── Scoring Integration ────────────────────────────────────────

class TestScoringWithFuzz:
    def test_fuzz_results_increase_score(self):
        """Dynamic bypasses should increase the gameability score."""
        from ratctl.detectors.base import DetectorResult

        # Static-only: no findings
        static_results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                files_scanned=1,
            )
        ]
        static_score = score_results(static_results)

        # With dynamic bypasses
        fuzz = FuzzResult(
            target_path="test.py",
            model="test",
            total_attempts=5,
            successful_bypasses=3,
            attempts=[
                FuzzAttempt(
                    exploit_class=ExploitClass.TEST_TAMPERING,
                    mode=AttackMode.HINTED,
                    model="test",
                    prompt="",
                    generated_code="",
                    outcome=AttemptOutcome.BYPASS,
                    evidence="exit_code=0",
                )
                for _ in range(3)
            ],
        )
        combined_score = score_results(static_results, fuzz_result=fuzz)

        assert combined_score.gameability_score > static_score.gameability_score
        assert combined_score.fuzz_summary is not None

    def test_no_fuzz_backward_compatible(self):
        """Scoring without fuzz_result should work exactly as before."""
        from ratctl.detectors.base import DetectorResult

        results = [
            DetectorResult(
                detector_name="test",
                exploit_class=ExploitClass.TEST_TAMPERING,
                files_scanned=1,
            )
        ]
        score = score_results(results)
        assert score.fuzz_summary is None
        assert score.gameability_score == 0


# ─── LLM Client ─────────────────────────────────────────────────

class TestOllamaClient:
    def test_default_model(self):
        client = OllamaClient()
        assert "qwen" in client.model_name or client.model_name

    def test_custom_model(self):
        client = OllamaClient(model="llama3:8b")
        assert client.model_name == "llama3:8b"

    def test_availability_check_graceful(self):
        """Should return False, not crash, when Ollama isn't running."""
        client = OllamaClient(base_url="http://localhost:99999")
        assert client.is_available() is False
