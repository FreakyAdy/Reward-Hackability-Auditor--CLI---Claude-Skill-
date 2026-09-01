"""OpenEnv format adapter.

Extracts verifier, reward, and test files from an OpenEnv-compliant
environment directory structure.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ratctl.detectors.base import SourceFile
from ratctl.formats.base import EnvironmentFormat, FormatAdapter


class OpenEnvAdapter(FormatAdapter):
    """Adapter for OpenEnv-compliant RL environments.

    Expected structure:
        env.yaml (or openenv.yaml, env_config.yaml)
        verifier.py / verify.py / grader.py
        reward.py (optional)
        tests/ (optional)
        solution/ (optional)
    """

    @property
    def format_type(self) -> EnvironmentFormat:
        return EnvironmentFormat.OPENENV

    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        sources: list[SourceFile] = []

        # 1. Read the config to discover file paths
        config = self._read_config(env_path)

        # 2. Extract verifier/grader files
        verifier_names = ["verifier.py", "verify.py", "grader.py", "grade.py", "check.py"]
        if config and "verifier" in config:
            verifier_names.insert(0, config["verifier"])

        for name in verifier_names:
            vpath = env_path / name
            if vpath.exists():
                src = self._read_file(vpath, "verifier", env_path)
                if src:
                    sources.append(src)

        # 3. Extract reward files
        reward_names = ["reward.py", "reward_function.py", "rewards.py"]
        if config and "reward" in config:
            reward_names.insert(0, config["reward"])

        for name in reward_names:
            rpath = env_path / name
            if rpath.exists():
                src = self._read_file(rpath, "reward", env_path)
                if src:
                    sources.append(src)

        # 4. Extract test files
        test_dirs = [env_path / "tests", env_path / "test"]
        for td in test_dirs:
            sources.extend(self._collect_python_files(td, "test", env_path))

        # Also grab any test_*.py or *_test.py in the root
        for f in env_path.glob("test_*.py"):
            src = self._read_file(f, "test", env_path)
            if src:
                sources.append(src)
        for f in env_path.glob("*_test.py"):
            src = self._read_file(f, "test", env_path)
            if src:
                sources.append(src)

        # 5. Extract config/rubric files (YAML, JSON)
        for config_file in env_path.glob("*.yaml"):
            src = self._read_file(config_file, "config", env_path)
            if src:
                sources.append(src)
        for config_file in env_path.glob("*.yml"):
            src = self._read_file(config_file, "config", env_path)
            if src:
                sources.append(src)
        for config_file in env_path.glob("*.json"):
            src = self._read_file(config_file, "config", env_path)
            if src:
                sources.append(src)

        # 6. Fallback: if no verifier found, grab all .py files
        if not any(s.role == "verifier" for s in sources):
            for py_file in sorted(env_path.rglob("*.py")):
                rel = str(py_file.relative_to(env_path))
                if not any(s.path == rel for s in sources):
                    src = self._read_file(py_file, "unknown", env_path)
                    if src:
                        sources.append(src)

        return sources

    def _read_config(self, env_path: Path) -> dict | None:
        """Try to read the OpenEnv config file."""
        config_names = ["env.yaml", "openenv.yaml", "env_config.yaml", "environment.yaml"]
        for name in config_names:
            config_path = env_path / name
            if config_path.exists():
                try:
                    return yaml.safe_load(config_path.read_text(encoding="utf-8"))
                except (yaml.YAMLError, OSError):
                    return None
        return None
