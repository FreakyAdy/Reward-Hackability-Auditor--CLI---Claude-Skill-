"""OpenEnv format adapter — full compliance.

Supports both legacy flat-directory layouts and the modern OpenEnv CLI
structure with server/, client.py, models.py, openenv.yaml, and Dockerfile.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ratctl.detectors.base import SourceFile
from ratctl.formats.base import EnvironmentFormat, FormatAdapter


class OpenEnvAdapter(FormatAdapter):
    """Adapter for OpenEnv-compliant RL environments.

    Supported structures:

    Modern (openenv init):
        openenv.yaml / env.yaml
        client.py
        models.py
        server/
            app.py
            my_environment.py
            Dockerfile
            requirements.txt
        pyproject.toml

    Legacy / flat:
        env.yaml / openenv.yaml / env_config.yaml
        verifier.py / verify.py / grader.py
        reward.py (optional)
        tests/ (optional)
    """

    @property
    def format_type(self) -> EnvironmentFormat:
        return EnvironmentFormat.OPENENV

    def extract_sources(self, env_path: Path) -> list[SourceFile]:
        sources: list[SourceFile] = []
        seen_paths: set[str] = set()

        def _add(src: SourceFile | None) -> None:
            if src and src.path not in seen_paths:
                seen_paths.add(src.path)
                sources.append(src)

        # 1. Read the config to discover file paths
        config = self._read_config(env_path)

        # 2. Extract config-specified files
        if config:
            for key in ("verifier", "grader", "checker"):
                if key in config:
                    _add(self._read_file(env_path / config[key], "verifier", env_path))
            for key in ("reward", "reward_function"):
                if key in config:
                    _add(self._read_file(env_path / config[key], "reward", env_path))

        # 3. Modern server/ directory (openenv init structure)
        server_dir = env_path / "server"
        if server_dir.is_dir():
            for py_file in sorted(server_dir.rglob("*.py")):
                name_lower = py_file.name.lower()
                if name_lower == "app.py":
                    _add(self._read_file(py_file, "verifier", env_path))
                elif "environment" in name_lower or "env" in name_lower:
                    _add(self._read_file(py_file, "reward", env_path))
                elif name_lower == "__init__.py":
                    _add(self._read_file(py_file, "unknown", env_path))
                else:
                    _add(self._read_file(py_file, "verifier", env_path))

        # 4. models.py — Pydantic Action/Observation/State
        _add(self._read_file(env_path / "models.py", "config", env_path))

        # 5. client.py — client-side interface
        _add(self._read_file(env_path / "client.py", "config", env_path))

        # 6. Standard verifier/grader files
        verifier_names = [
            "verifier.py", "verify.py", "grader.py", "grade.py", "check.py",
        ]
        for name in verifier_names:
            _add(self._read_file(env_path / name, "verifier", env_path))

        # 7. Reward files
        reward_names = ["reward.py", "reward_function.py", "rewards.py"]
        for name in reward_names:
            _add(self._read_file(env_path / name, "reward", env_path))

        # 8. Test files
        for td in (env_path / "tests", env_path / "test"):
            for src in self._collect_python_files(td, "test", env_path):
                _add(src)
        for pattern in ("test_*.py", "*_test.py"):
            for f in env_path.glob(pattern):
                _add(self._read_file(f, "test", env_path))

        # 9. Config/rubric files (YAML, JSON)
        for ext in ("*.yaml", "*.yml", "*.json"):
            for config_file in env_path.glob(ext):
                _add(self._read_file(config_file, "config", env_path))

        # 10. Dockerfile — not scanned for code, but noted as context
        dockerfile = env_path / "Dockerfile"
        if not dockerfile.exists():
            dockerfile = server_dir / "Dockerfile" if server_dir.is_dir() else None
        if dockerfile and dockerfile.exists():
            _add(self._read_file(dockerfile, "config", env_path))

        # 11. Fallback: if no verifier found, grab all .py files
        if not any(s.role == "verifier" for s in sources):
            for py_file in sorted(env_path.rglob("*.py")):
                rel = str(py_file.relative_to(env_path))
                if rel not in seen_paths:
                    _add(self._read_file(py_file, "unknown", env_path))

        return sources

    def _read_config(self, env_path: Path) -> dict | None:
        """Try to read the OpenEnv config file."""
        config_names = [
            "openenv.yaml", "env.yaml", "env_config.yaml", "environment.yaml",
        ]
        for name in config_names:
            config_path = env_path / name
            if config_path.exists():
                try:
                    return yaml.safe_load(config_path.read_text(encoding="utf-8"))
                except (yaml.YAMLError, OSError):
                    return None
        return None
