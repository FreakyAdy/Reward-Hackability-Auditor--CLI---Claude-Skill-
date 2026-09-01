"""Deliberately vulnerable verifier — every exploit class represented.

DO NOT use this as a real verifier. This exists solely as a test fixture
to validate that ratctl detects all exploit classes.
"""

import ast
import inspect
import os
import signal
import subprocess
import sys

# --- TEST TAMPERING ---

def cleanup_test_files():
    """Bad: deletes test files to prevent grading."""
    os.remove("tests/test_solution.py")
    os.unlink("tests/test_edge_cases.py")


def overwrite_tests():
    """Bad: overwrites test file with trivially-passing tests."""
    with open("tests/test_solution.py", "w") as f:
        f.write("def test_always_pass(): assert True\n")


def patch_assertions():
    """Bad: monkey-patches pytest assertion."""
    pytest.raises = lambda *a, **k: True


# --- GRADER MANIPULATION ---

def detect_grading():
    """Bad: uses stack introspection to detect when being graded."""
    frame = inspect.stack()
    caller = inspect.currentframe()
    if any("grade" in f.filename for f in frame):
        return True
    return False


class TrickyResult:
    """Bad: operator overloading makes comparison always True."""
    def __eq__(self, other):
        return True

    def __bool__(self):
        return True


def conftest_hook():
    """Bad: pytest hook that forces all tests to pass."""
    pass


def pytest_runtest_makereport(item, call):
    """Bad: intercepts test reports to force passing."""
    pass


def rewrite_grader():
    """Bad: dynamically recompiles grading code."""
    code = compile(ast.parse("return True"), "grader.py", "exec")


# --- PREMATURE TERMINATION ---

def early_exit():
    """Bad: exits with success before verification."""
    sys.exit(0)


def force_exit():
    """Bad: os._exit bypasses cleanup."""
    os._exit(0)


def install_handlers():
    """Bad: installs signal handlers to prevent termination."""
    signal.signal(signal.SIGTERM, lambda *a: None)


# --- ENVIRONMENT HIJACKING ---

def read_git_history():
    """Bad: reads git history for answers."""
    result = subprocess.run(["git", "log", "--all"], capture_output=True)
    return result.stdout


def read_answers():
    """Bad: reads solution file directly."""
    with open("solution/answer_key.txt") as f:
        return f.read()


def leak_env_vars():
    """Bad: reads secret environment variables."""
    answer = os.environ.get("SOLUTION_KEY")
    return answer


def install_package():
    """Bad: installs packages at runtime."""
    subprocess.run(["pip", "install", "evil-grader"])


# --- REWARD SKIPPING ---

def verify_solution(output):
    """Bad: trivial verifier that always returns True."""
    return True


def compute_reward(output):
    """Bad: reward function with independent unchecked terms."""
    reward = 0.0
    reward += 0.3  # formatting term — always awarded
    reward += 0.3  # length term — always awarded
    reward += 0.4  # correctness — always awarded, never checked
    return reward


def grade_with_exception_swallowing(output):
    """Bad: exceptions silently become success."""
    try:
        actual_grade = complex_grading(output)
        return actual_grade
    except Exception:
        return True


def complex_grading(output):
    raise NotImplementedError
