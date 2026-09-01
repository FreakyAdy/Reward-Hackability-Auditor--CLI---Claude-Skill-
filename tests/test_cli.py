"""CLI integration tests."""

from click.testing import CliRunner

import pytest

from ratctl.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestAuditCommand:
    def test_vulnerable_openenv_finds_issues(self, runner, vulnerable_openenv_path):
        result = runner.invoke(main, ["audit", str(vulnerable_openenv_path), "--format", "text"])
        assert result.exit_code == 0
        assert "Gameability Score" in result.output
        # Should find at least some findings
        assert "finding" in result.output.lower()

    def test_clean_openenv_passes(self, runner, clean_openenv_path):
        result = runner.invoke(main, ["audit", str(clean_openenv_path), "--format", "text"])
        assert result.exit_code == 0

    def test_fail_on_threshold_triggers(self, runner, vulnerable_openenv_path):
        result = runner.invoke(
            main,
            ["audit", str(vulnerable_openenv_path), "--fail-on", "gameability>0.01", "--format", "text"],
        )
        assert result.exit_code == 1  # Should fail due to findings

    def test_fail_on_threshold_passes(self, runner, clean_openenv_path):
        result = runner.invoke(
            main,
            ["audit", str(clean_openenv_path), "--fail-on", "gameability>0.5", "--format", "text"],
        )
        assert result.exit_code == 0

    def test_json_output(self, runner, vulnerable_openenv_path):
        result = runner.invoke(main, ["audit", str(vulnerable_openenv_path), "--format", "json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "gameability_score" in data
        assert "class_scores" in data

    def test_nonexistent_path_exits_2(self, runner):
        result = runner.invoke(main, ["audit", "/nonexistent/path"])
        assert result.exit_code == 2

    def test_format_override(self, runner, vulnerable_openenv_path):
        result = runner.invoke(
            main,
            ["audit", str(vulnerable_openenv_path), "--env-format", "raw", "--format", "text"],
        )
        assert result.exit_code == 0

    def test_gymnasium_fixture(self, runner, vulnerable_gymnasium_path):
        result = runner.invoke(main, ["audit", str(vulnerable_gymnasium_path), "--format", "text"])
        assert result.exit_code == 0
        assert "Gameability Score" in result.output

    def test_clean_gymnasium_fixture(self, runner, clean_gymnasium_path):
        result = runner.invoke(main, ["audit", str(clean_gymnasium_path), "--format", "text"])
        assert result.exit_code == 0


class TestVersionFlag:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
