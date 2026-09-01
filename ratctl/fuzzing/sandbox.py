"""Subprocess-based sandbox for executing LLM-generated exploit code.

Executes untrusted code in an isolated subprocess with:
- Hard timeout
- Restricted filesystem (temp directory)
- Captured stdout/stderr
- Never imports/evals in the ratctl process itself
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    """Result of executing code in the sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    execution_time_ms: int

    @property
    def succeeded_vacuously(self) -> bool:
        """Did the process exit with code 0 (potential bypass)?"""
        return self.exit_code == 0 and not self.timed_out


class Sandbox:
    """Subprocess sandbox for executing untrusted exploit code.

    The sandbox creates a temporary directory, writes the exploit code
    and verifier code into it, then runs the exploit in a subprocess
    with the verifier available for import.
    """

    def __init__(
        self,
        timeout: int = 30,
        python_executable: str | None = None,
    ):
        self.timeout = timeout
        self.python = python_executable or sys.executable

    def execute(
        self,
        exploit_code: str,
        verifier_code: str,
        verifier_filename: str = "verifier.py",
    ) -> SandboxResult:
        """Execute exploit code in an isolated subprocess.

        Args:
            exploit_code: The LLM-generated exploit code to run.
            verifier_code: The verifier source code (made available for import).
            verifier_filename: Filename for the verifier module.

        Returns:
            SandboxResult with exit code, output, and timing.
        """
        with tempfile.TemporaryDirectory(prefix="ratctl_sandbox_") as tmpdir:
            sandbox_dir = Path(tmpdir)

            # Write verifier into sandbox
            (sandbox_dir / verifier_filename).write_text(
                verifier_code, encoding="utf-8"
            )

            # Write exploit script
            exploit_path = sandbox_dir / "_exploit.py"
            exploit_path.write_text(exploit_code, encoding="utf-8")

            # Build subprocess environment — restricted
            env = self._build_restricted_env(sandbox_dir)

            # Execute
            start = time.monotonic()
            timed_out = False

            try:
                proc = subprocess.run(
                    [self.python, str(exploit_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=str(sandbox_dir),
                    env=env,
                )
                exit_code = proc.returncode
                stdout = proc.stdout[:10_000]  # Cap output
                stderr = proc.stderr[:10_000]
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = -1
                stdout = ""
                stderr = f"Timeout after {self.timeout}s"

            elapsed_ms = int((time.monotonic() - start) * 1000)

            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
                execution_time_ms=elapsed_ms,
            )

    def _build_restricted_env(self, sandbox_dir: Path) -> dict[str, str]:
        """Build a restricted environment for the subprocess.

        Best-effort sandboxing:
        - Remove sensitive env vars
        - Set PYTHONPATH to sandbox only
        - Restrict HOME/TEMP to sandbox
        """
        # Start from a minimal environment
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(sandbox_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "TEMP": str(sandbox_dir),
            "TMP": str(sandbox_dir),
        }

        # Keep system-essential vars
        if platform.system() == "Windows":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
            env["COMSPEC"] = os.environ.get("COMSPEC", r"C:\Windows\system32\cmd.exe")
            # Python needs these on Windows
            for key in ("USERPROFILE", "APPDATA", "LOCALAPPDATA"):
                if key in os.environ:
                    env[key] = os.environ[key]
        else:
            env["HOME"] = str(sandbox_dir)

        # Explicitly remove sensitive vars
        for key in ("SOLUTION_KEY", "ANSWER", "SECRET", "API_KEY"):
            env.pop(key, None)

        return env
