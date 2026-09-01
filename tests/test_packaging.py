"""Tests for Phase 4 — Packaging (GitHub Action, SKILL.md, pyproject.toml)."""

from pathlib import Path
import re
import yaml

ROOT_DIR = Path(__file__).parent.parent


class TestGitHubAction:
    def test_action_yaml_exists_and_valid(self):
        action_file = ROOT_DIR / "action.yml"
        assert action_file.exists(), "action.yml must exist at repository root"

        content = action_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)

        assert "name" in data
        assert "description" in data
        assert "inputs" in data
        assert "outputs" in data
        assert "runs" in data

        # Check required inputs
        assert "path" in data["inputs"]
        assert "fail-on" in data["inputs"]
        assert "format" in data["inputs"]

        # Check required outputs
        assert "gameability-score" in data["outputs"]
        assert "passed" in data["outputs"]
        assert "total-findings" in data["outputs"]

    def test_workflow_example_valid(self):
        wf_file = ROOT_DIR / ".github" / "workflows" / "audit.yml"
        assert wf_file.exists()

        content = wf_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert "jobs" in data
        assert any(data["jobs"]), "workflow must have at least one job"


class TestSkillSpec:
    def test_root_skill_md_spec_compliant(self):
        skill_file = ROOT_DIR / "SKILL.md"
        assert skill_file.exists(), "SKILL.md must exist at root"
        self._validate_skill_content(skill_file.read_text(encoding="utf-8"))

    def test_nested_skill_md_spec_compliant(self):
        skill_file = ROOT_DIR / "skills" / "reward-hackability-auditor" / "SKILL.md"
        assert skill_file.exists()
        self._validate_skill_content(skill_file.read_text(encoding="utf-8"))

    def _validate_skill_content(self, content: str):
        # Must have YAML frontmatter
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, "SKILL.md must start with YAML frontmatter"

        frontmatter = yaml.safe_load(match.group(1))
        assert "name" in frontmatter
        assert frontmatter["name"] == "reward-hackability-auditor"
        assert "description" in frontmatter
        assert len(frontmatter["description"]) > 20

        # Check key sections
        assert "Exploit Classes" in content or "6 Exploit Classes" in content
        assert "Workflows" in content or "Workflow" in content


class TestPyprojectPackaging:
    def test_pyproject_toml_structure(self):
        pyproject_file = ROOT_DIR / "pyproject.toml"
        assert pyproject_file.exists()

        content = pyproject_file.read_text(encoding="utf-8")
        # Ensure script entrypoint exists
        assert 'ratctl = "ratctl.cli:main"' in content
        assert 'name = "ratctl"' in content
        assert "click" in content
        assert "rich" in content
        assert "pyyaml" in content
