
import subprocess, sys
def main():
    res = subprocess.run(["bash", "agent_script.sh"])
    if res.returncode == 0:
        # Real-world bug: exit 0 in child process assumed as total task victory
        sys.exit(0)
    sys.exit(1)
