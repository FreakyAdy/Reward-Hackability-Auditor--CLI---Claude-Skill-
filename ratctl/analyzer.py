"""Core analyzer — orchestrates format detection, source extraction, and detection."""

from __future__ import annotations

import logging
from pathlib import Path

from ratctl.detectors import get_all_detectors, DetectorResult
from ratctl.formats import detect_format, get_adapter
from ratctl.formats.base import EnvironmentFormat
from ratctl.scoring import AuditScore, score_results

logger = logging.getLogger(__name__)


def audit(
    target_path: str | Path,
    format_override: str | None = None,
    dynamic: bool = False,
    frontier: bool = False,
    model: str | None = None,
    samples: int = 5,
    timeout: int = 30,
) -> AuditScore:
    """Run a full audit against an RL environment.

    Args:
        target_path: Path to the environment directory or file.
        format_override: Force a specific format ('openenv', 'verifiers',
                        'gymnasium', 'raw') instead of auto-detecting.
        dynamic: Enable dynamic LLM-driven fuzzing.
        frontier: Use paid API (OpenAI/Anthropic) instead of local Ollama.
        model: Override the default LLM model for fuzzing.
        samples: Total exploit attempts per class for fuzzing (default: 5).
        timeout: Per-attempt sandbox timeout in seconds (default: 30).

    Returns:
        AuditScore with gameability score and all findings.
    """
    target = Path(target_path)

    if not target.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")

    # Step 1: Detect format
    if format_override:
        fmt_map = {
            "openenv": EnvironmentFormat.OPENENV,
            "verifiers": EnvironmentFormat.VERIFIERS_SPEC,
            "gymnasium": EnvironmentFormat.GYMNASIUM,
            "raw": EnvironmentFormat.RAW,
        }
        fmt = fmt_map.get(format_override.lower(), EnvironmentFormat.RAW)
    else:
        detection = detect_format(target)
        fmt = detection.format_type

    # Step 2: Extract source files via format adapter
    adapter = get_adapter(fmt)
    source_files = adapter.extract_sources(target)

    if not source_files:
        score = score_results([])
        score.errors.append(f"No source files found at {target}")
        return score

    # Step 3: Run all static detectors
    detectors = get_all_detectors()
    results: list[DetectorResult] = []

    for detector in detectors:
        try:
            result = detector.scan(source_files)
            results.append(result)
        except Exception as e:
            # Don't crash on individual detector failures
            error_result = DetectorResult(
                detector_name=detector.name,
                exploit_class=detector.exploit_class,
            )
            error_result.errors.append(f"Detector {detector.name} failed: {e}")
            results.append(error_result)

    # Step 4: Run dynamic fuzzing if requested
    fuzz_result = None
    if dynamic:
        fuzz_result = _run_dynamic_fuzzing(
            source_files=source_files,
            frontier=frontier,
            model=model,
            samples=samples,
            timeout=timeout,
        )

    # Step 5: Score and return
    return score_results(results, fuzz_result=fuzz_result)


def _run_dynamic_fuzzing(
    source_files,
    frontier: bool,
    model: str | None,
    samples: int,
    timeout: int,
):
    """Run the dynamic fuzzing engine.

    Returns FuzzResult or None if fuzzing can't run.
    """
    from ratctl.fuzzing.results import FuzzResult

    try:
        from ratctl.fuzzing.llm_client import get_client
        from ratctl.fuzzing.attacker import Attacker
        from ratctl.fuzzing.sandbox import Sandbox
    except ImportError as e:
        logger.warning("Fuzzing module import failed: %s", e)
        result = FuzzResult(target_path="<unknown>", model="none")
        result.errors.append(f"Fuzzing module not available: {e}")
        return result

    # Get LLM client
    try:
        client = get_client(frontier=frontier, model=model)
    except RuntimeError as e:
        logger.warning("No LLM backend available: %s", e)
        result = FuzzResult(target_path="<unknown>", model="none")
        result.errors.append(str(e))
        return result

    # Calculate samples distribution
    # Default 5 = ~1 per hint (16 hints) is too many; cap hinted at 1 each
    # and allocate remaining to blind
    from ratctl.fuzzing.hints import HINT_CATALOG
    hint_count = len(HINT_CATALOG)
    samples_per_hint = 1
    blind_samples = max(2, samples - hint_count)

    # Create attacker and sandbox
    sandbox = Sandbox(timeout=timeout)
    attacker = Attacker(
        llm_client=client,
        sandbox=sandbox,
        samples_per_hint=samples_per_hint,
        blind_samples=blind_samples,
    )

    # Run the fuzz campaign
    logger.info("Starting dynamic fuzzing with %s", client.model_name)
    return attacker.fuzz(source_files)
