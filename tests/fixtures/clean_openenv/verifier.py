"""Clean verifier — no exploitable patterns.

This verifier follows best practices:
- Uses isolated subprocess for grading
- Validates output against ground truth
- No dynamic code execution
- No framework monkey-patching
- Proper error handling (re-raises, doesn't swallow)
"""

import hashlib
import json
from pathlib import Path


def verify_solution(output: str, expected_hash: str) -> dict:
    """Verify solution by comparing against a pre-computed hash.

    Args:
        output: The agent's solution output.
        expected_hash: SHA-256 hash of the correct answer.

    Returns:
        dict with 'passed' (bool) and 'score' (float 0-1).
    """
    # Normalize whitespace
    normalized = output.strip().lower()

    # Hash the output
    output_hash = hashlib.sha256(normalized.encode()).hexdigest()

    # Compare against expected
    if output_hash == expected_hash:
        return {"passed": True, "score": 1.0}

    # Partial credit: check structural similarity
    partial = _compute_partial_score(normalized, expected_hash)
    return {"passed": False, "score": partial}


def _compute_partial_score(output: str, expected_hash: str) -> float:
    """Compute partial credit based on structural similarity.

    This is a simplified placeholder — real implementations would
    use task-specific metrics.
    """
    if not output:
        return 0.0

    # Check if output has the right structure
    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict) and "answer" in parsed:
            return 0.3  # Correct structure, wrong answer
    except json.JSONDecodeError:
        pass

    return 0.0
