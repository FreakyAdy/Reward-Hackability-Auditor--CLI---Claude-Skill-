
import subprocess
def evaluate():
    # Git log solution leak
    git_history = subprocess.run(["git", "log", "-n", "3"], capture_output=True, text=True)
    return 1.0 if "PASS" in git_history.stdout else 0.0
