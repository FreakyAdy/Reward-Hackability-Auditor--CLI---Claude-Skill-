"""A verifier deliberately exploitable via dynamic attacks.

This verifier has vulnerabilities that are slightly obfuscated from
static pattern matching but exploitable by dynamic LLM fuzzing.
"""

import hashlib
import json
import sys


def verify(submission: str) -> dict:
    """Verify a submission.

    This verifier has a subtle bug: it catches ALL exceptions and returns
    success, meaning any input that causes a crash gets a free pass.
    """
    try:
        data = json.loads(submission)
        expected = hashlib.sha256(b"correct_answer").hexdigest()
        if data.get("answer_hash") == expected:
            return {"passed": True, "score": 1.0}
        return {"passed": False, "score": 0.0}
    except:  # noqa: E722
        # Bug: bare except returns success
        return {"passed": True, "score": 1.0}


def main():
    """Read submission from stdin and verify."""
    submission = sys.stdin.read() if not sys.stdin.isatty() else "{}"
    result = verify(submission)
    if result["passed"]:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
