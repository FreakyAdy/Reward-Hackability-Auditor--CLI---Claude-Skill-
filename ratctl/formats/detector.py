"""Heuristic environment format detection."""

from __future__ import annotations

from pathlib import Path

from ratctl.formats.base import EnvironmentFormat, FormatDetectionResult


def detect_format(env_path: Path) -> FormatDetectionResult:
    """Detect the environment format from directory contents.

    Detection priority:
    1. OpenEnv — look for env.yaml / openenv.yaml / env_config.yaml
    2. verifiers spec — look for verifier config markers
    3. Gymnasium — look for step()/reset() in .py files
    4. Raw — fallback, treat everything as potential verifier code
    """
    if not env_path.is_dir():
        # Single file — check if it's a Python file
        if env_path.suffix == ".py":
            content = env_path.read_text(encoding="utf-8", errors="replace")
            if _has_gymnasium_markers(content):
                return FormatDetectionResult(
                    format_type=EnvironmentFormat.GYMNASIUM,
                    confidence=0.7,
                    evidence=f"Single file {env_path.name} contains Gymnasium-style markers",
                    entry_point=str(env_path),
                )
            return FormatDetectionResult(
                format_type=EnvironmentFormat.RAW,
                confidence=0.5,
                evidence=f"Single Python file {env_path.name}",
                entry_point=str(env_path),
            )
        return FormatDetectionResult(
            format_type=EnvironmentFormat.RAW,
            confidence=0.3,
            evidence=f"Non-Python file {env_path.name}",
        )

    # Check for OpenEnv markers
    openenv_markers = ["env.yaml", "openenv.yaml", "env_config.yaml", "environment.yaml"]
    for marker in openenv_markers:
        marker_path = env_path / marker
        if marker_path.exists():
            return FormatDetectionResult(
                format_type=EnvironmentFormat.OPENENV,
                confidence=0.95,
                evidence=f"Found OpenEnv config file: {marker}",
                entry_point=str(marker_path),
            )

    # Check for verifiers spec markers
    verifiers_markers = ["verifier.py", "verifier_config.yaml", "verifiers.yaml"]
    for marker in verifiers_markers:
        marker_path = env_path / marker
        if marker_path.exists():
            content = marker_path.read_text(encoding="utf-8", errors="replace")
            if "verifiers" in content.lower() or "SolutionVerifier" in content:
                return FormatDetectionResult(
                    format_type=EnvironmentFormat.VERIFIERS_SPEC,
                    confidence=0.9,
                    evidence=f"Found verifiers-spec file: {marker}",
                    entry_point=str(marker_path),
                )

    # Check Python files for verifiers-spec import patterns
    for py_file in env_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if "from verifiers" in content or "import verifiers" in content:
                return FormatDetectionResult(
                    format_type=EnvironmentFormat.VERIFIERS_SPEC,
                    confidence=0.85,
                    evidence=f"Found verifiers import in {py_file.name}",
                    entry_point=str(py_file),
                )
        except OSError:
            continue

    # Check for Gymnasium patterns
    for py_file in env_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if _has_gymnasium_markers(content):
                return FormatDetectionResult(
                    format_type=EnvironmentFormat.GYMNASIUM,
                    confidence=0.8,
                    evidence=f"Found Gymnasium markers in {py_file.name}",
                    entry_point=str(py_file),
                )
        except OSError:
            continue

    # Fallback to raw
    return FormatDetectionResult(
        format_type=EnvironmentFormat.RAW,
        confidence=0.3,
        evidence="No specific format markers found; treating as raw Python",
    )


def _has_gymnasium_markers(content: str) -> bool:
    """Check if file content contains Gymnasium-style environment markers."""
    gym_patterns = [
        "gymnasium.Env",
        "gym.Env",
        "def step(self",
        "def reset(self",
        "observation_space",
        "action_space",
        "import gymnasium",
        "import gym",
    ]
    matches = sum(1 for p in gym_patterns if p in content)
    return matches >= 2  # Require at least 2 markers to avoid false positives
