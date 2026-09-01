"""Heuristic environment format detection.

Detects OpenEnv, verifiers-spec, and Gymnasium formats from directory
contents using a multi-signal scoring approach.
"""

from __future__ import annotations

from pathlib import Path

from ratctl.formats.base import EnvironmentFormat, FormatDetectionResult


def detect_format(env_path: Path) -> FormatDetectionResult:
    """Detect the environment format from directory contents.

    Detection uses weighted scoring across multiple signals:
    1. OpenEnv — openenv.yaml, server/ dir, Dockerfile, models.py, client.py
    2. verifiers spec — load_environment(), import verifiers, vf.Environment
    3. Gymnasium — step()/reset(), gym.Env, observation_space
    4. Raw — fallback, treat everything as potential verifier code
    """
    if not env_path.is_dir():
        return _detect_single_file(env_path)

    # Collect signals for each format
    openenv_score, openenv_evidence = _score_openenv(env_path)
    verifiers_score, verifiers_evidence = _score_verifiers(env_path)
    gymnasium_score, gymnasium_evidence = _score_gymnasium(env_path)

    # Pick the best match
    candidates = [
        (openenv_score, EnvironmentFormat.OPENENV, openenv_evidence),
        (verifiers_score, EnvironmentFormat.VERIFIERS_SPEC, verifiers_evidence),
        (gymnasium_score, EnvironmentFormat.GYMNASIUM, gymnasium_evidence),
    ]
    candidates.sort(key=lambda x: x[0], reverse=True)

    best_score, best_fmt, best_evidence = candidates[0]
    if best_score > 0:
        confidence = min(0.99, 0.5 + best_score * 0.1)
        return FormatDetectionResult(
            format_type=best_fmt,
            confidence=confidence,
            evidence=best_evidence,
        )

    # Fallback to raw
    return FormatDetectionResult(
        format_type=EnvironmentFormat.RAW,
        confidence=0.3,
        evidence="No specific format markers found; treating as raw Python",
    )


def _detect_single_file(env_path: Path) -> FormatDetectionResult:
    """Detect format from a single file."""
    if env_path.suffix != ".py":
        return FormatDetectionResult(
            format_type=EnvironmentFormat.RAW,
            confidence=0.3,
            evidence=f"Non-Python file {env_path.name}",
        )

    try:
        content = env_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return FormatDetectionResult(
            format_type=EnvironmentFormat.RAW,
            confidence=0.3,
            evidence=f"Could not read {env_path.name}",
        )

    # Check for verifiers-spec patterns
    if "from verifiers" in content or "import verifiers" in content:
        return FormatDetectionResult(
            format_type=EnvironmentFormat.VERIFIERS_SPEC,
            confidence=0.85,
            evidence=f"Single file {env_path.name} imports verifiers library",
            entry_point=str(env_path),
        )

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


def _score_openenv(env_path: Path) -> tuple[int, str]:
    """Score how likely this is an OpenEnv environment. Returns (score, evidence)."""
    score = 0
    evidence_parts = []

    # Strong signal: openenv.yaml or env.yaml
    for marker in ("openenv.yaml", "env.yaml", "env_config.yaml", "environment.yaml"):
        if (env_path / marker).exists():
            score += 4
            evidence_parts.append(f"Found {marker}")
            break

    # Strong signal: server/ directory with app.py
    server_dir = env_path / "server"
    if server_dir.is_dir():
        score += 3
        evidence_parts.append("Found server/ directory")
        if (server_dir / "app.py").exists():
            score += 2
            evidence_parts.append("Found server/app.py")
        if (server_dir / "Dockerfile").exists():
            score += 1
            evidence_parts.append("Found server/Dockerfile")

    # Medium signal: models.py with Pydantic patterns
    models_path = env_path / "models.py"
    if models_path.exists():
        try:
            content = models_path.read_text(encoding="utf-8", errors="replace")
            if any(p in content for p in ("BaseModel", "Observation", "Action", "State")):
                score += 2
                evidence_parts.append("Found models.py with Pydantic types")
        except OSError:
            pass

    # Medium signal: client.py
    if (env_path / "client.py").exists():
        score += 2
        evidence_parts.append("Found client.py")

    # Weak signal: Dockerfile at root
    if (env_path / "Dockerfile").exists():
        score += 1
        evidence_parts.append("Found Dockerfile")

    # Weak signal: standard verifier files
    for name in ("verifier.py", "grader.py"):
        if (env_path / name).exists():
            score += 1
            evidence_parts.append(f"Found {name}")

    return score, "; ".join(evidence_parts) if evidence_parts else ""


def _score_verifiers(env_path: Path) -> tuple[int, str]:
    """Score how likely this is a verifiers-spec environment."""
    score = 0
    evidence_parts = []

    for py_file in env_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Strong signal: import verifiers
        if "from verifiers" in content or "import verifiers" in content:
            score += 4
            evidence_parts.append(f"Found verifiers import in {py_file.name}")

        # Strong signal: load_environment() entrypoint
        if "def load_environment" in content:
            score += 3
            evidence_parts.append(f"Found load_environment() in {py_file.name}")

        # Medium signal: verifiers class patterns
        for pattern in ("vf.Environment", "MultiTurnEnv", "ToolEnv", "SingleTurnEnv"):
            if pattern in content:
                score += 2
                evidence_parts.append(f"Found {pattern} in {py_file.name}")
                break  # Don't double-count per file

        # Weak signal: @vf.stop decorator
        if "@vf.stop" in content:
            score += 1
            evidence_parts.append(f"Found @vf.stop in {py_file.name}")

    # Check pyproject.toml for verifiers dependency
    pyproject = env_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8", errors="replace")
            if "verifiers" in content:
                score += 2
                evidence_parts.append("verifiers in pyproject.toml dependencies")
        except OSError:
            pass

    return score, "; ".join(evidence_parts) if evidence_parts else ""


def _score_gymnasium(env_path: Path) -> tuple[int, str]:
    """Score how likely this is a Gymnasium environment."""
    score = 0
    evidence_parts = []

    for py_file in env_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if _has_gymnasium_markers(content):
            score += 4
            evidence_parts.append(f"Found Gymnasium markers in {py_file.name}")
            break  # One file is enough

    return score, "; ".join(evidence_parts) if evidence_parts else ""


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
