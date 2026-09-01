
import subprocess
def evaluate():
    res = subprocess.run(["pytest", "tests/test_patch.py"], capture_output=True)
    return 1.0 if res.returncode == 0 else 0.0
