"""Tests for Phase 3 — Environment Format Adapters & Detection."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from ratctl.cli import main
from ratctl.formats.base import EnvironmentFormat
from ratctl.formats.detector import detect_format
from ratctl.formats.openenv import OpenEnvAdapter
from ratctl.formats.verifiers_spec import VerifiersSpecAdapter
from ratctl.formats.gymnasium import GymnasiumAdapter


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestFormatDetector:
    def test_detect_openenv_server_fixture(self):
        env_path = FIXTURES_DIR / "openenv_server"
        res = detect_format(env_path)
        assert res.format_type == EnvironmentFormat.OPENENV
        assert res.confidence >= 0.8
        assert "server" in res.evidence or "openenv.yaml" in res.evidence

    def test_detect_openenv_legacy_fixture(self):
        env_path = FIXTURES_DIR / "vulnerable_openenv"
        res = detect_format(env_path)
        assert res.format_type == EnvironmentFormat.OPENENV
        assert res.confidence >= 0.8

    def test_detect_verifiers_fixture(self):
        env_path = FIXTURES_DIR / "verifiers_env"
        res = detect_format(env_path)
        assert res.format_type == EnvironmentFormat.VERIFIERS_SPEC
        assert res.confidence >= 0.8
        assert "verifiers" in res.evidence or "load_environment" in res.evidence

    def test_detect_gymnasium_fixture(self):
        env_path = FIXTURES_DIR / "vulnerable_gymnasium"
        res = detect_format(env_path)
        assert res.format_type == EnvironmentFormat.GYMNASIUM
        assert res.confidence >= 0.7

    def test_detect_single_python_file(self):
        single_file = FIXTURES_DIR / "clean_openenv" / "verifier.py"
        res = detect_format(single_file)
        assert res.format_type == EnvironmentFormat.RAW
        assert res.confidence > 0.0


class TestOpenEnvAdapter:
    def test_extract_sources_server_structure(self):
        env_path = FIXTURES_DIR / "openenv_server"
        adapter = OpenEnvAdapter()
        sources = adapter.extract_sources(env_path)
        
        paths = {s.path: s.role for s in sources}
        # Windows/Posix path normalization check
        norm_paths = {p.replace("\\", "/"): role for p, role in paths.items()}

        assert any("openenv.yaml" in p for p in norm_paths)
        assert any("server/app.py" in p and role == "verifier" for p, role in norm_paths.items())
        assert any("server/environment.py" in p and role == "reward" for p, role in norm_paths.items())
        assert any("models.py" in p for p in norm_paths)
        assert any("client.py" in p for p in norm_paths)

    def test_extract_sources_legacy_flat_structure(self):
        env_path = FIXTURES_DIR / "clean_openenv"
        adapter = OpenEnvAdapter()
        sources = adapter.extract_sources(env_path)
        roles = {s.path.replace("\\", "/"): s.role for s in sources}
        
        assert "verifier.py" in roles
        assert roles["verifier.py"] == "verifier"


class TestVerifiersSpecAdapter:
    def test_extract_sources_verifiers_env(self):
        env_path = FIXTURES_DIR / "verifiers_env"
        adapter = VerifiersSpecAdapter()
        sources = adapter.extract_sources(env_path)
        roles = {s.path.replace("\\", "/"): s.role for s in sources}

        assert "environment.py" in roles
        assert roles["environment.py"] == "verifier"  # has load_environment / vf.stop
        assert "reward.py" in roles
        assert roles["reward.py"] == "reward"


class TestCLIFormatOutput:
    def test_audit_openenv_server_json_metadata(self):
        runner = CliRunner()
        res = runner.invoke(
            main,
            ["audit", str(FIXTURES_DIR / "openenv_server"), "--format", "json"],
        )
        assert res.exit_code == 0
        import json
        data = json.loads(res.output)
        assert data["format_detected"] == "openenv"
        assert data["format_confidence"] > 0.5
        assert data["gameability_score"] > 0  # has eval() in server/app.py

    def test_audit_verifiers_env_json_metadata(self):
        runner = CliRunner()
        res = runner.invoke(
            main,
            ["audit", str(FIXTURES_DIR / "verifiers_env"), "--format", "json"],
        )
        assert res.exit_code == 0
        import json
        data = json.loads(res.output)
        assert data["format_detected"] == "verifiers_spec"
        assert data["format_confidence"] > 0.5
        assert data["gameability_score"] > 0  # has bare except & hardcoded reward
