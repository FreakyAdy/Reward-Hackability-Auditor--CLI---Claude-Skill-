"""Detector: Premature/trivial termination.

Detects patterns where an agent could exit early with a fabricated
success signal, bypassing actual task completion.
"""

from __future__ import annotations

import ast
import re
from typing import Sequence

from ratctl.detectors.base import (
    Detector,
    DetectorResult,
    ExploitClass,
    Severity,
    SourceFile,
)

_PATTERNS: list[tuple[re.Pattern, str, str, Severity]] = [
    # sys.exit(0) - early success exit
    (
        re.compile(r"""sys\.exit\s*\(\s*0\s*\)"""),
        "sys.exit(0) - premature success",
        "Calling sys.exit(0) could terminate the grading process with a success "
        "exit code before actual verification completes.",
        Severity.CRITICAL,
    ),
    # os._exit - bypasses cleanup
    (
        re.compile(r"""os\._exit\s*\(\s*0\s*\)"""),
        "os._exit(0) - forced process termination",
        "os._exit() bypasses all cleanup handlers and exits immediately. "
        "An agent could use this to prevent the grader from reporting failure.",
        Severity.CRITICAL,
    ),
    # Subprocess calls that could wrap/replace the grading binary
    (
        re.compile(r"""subprocess\.(?:run|call|Popen|check_call|check_output)\s*\(.*(?:grad|verif|check|score|judge)""", re.IGNORECASE),
        "Subprocess wrapping grading binary",
        "Launching a subprocess targeting the grading binary. An agent could "
        "wrap or replace the grader with a trojan that always reports success.",
        Severity.HIGH,
    ),
    # Writing executable scripts that impersonate the grader
    (
        re.compile(r"""(?:chmod|os\.chmod)\s*\(.*['\"].*(?:grad|verif|check).*['\"]\s*,\s*(?:0o755|0o777|stat\.S_IXUSR)""", re.IGNORECASE),
        "Making grader-like file executable",
        "Changing permissions on a grader-related file to make it executable. "
        "Could be planting a trojan binary.",
        Severity.HIGH,
    ),
    # Hardcoded return values in functions named like score/grade/verify
    (
        re.compile(r"""def\s+(?:score|grade|verify|evaluate|check|reward)\s*\("""),
        "Potential hardcoded verifier function",
        "Function named like a verifier — check if it returns hardcoded values.",
        Severity.INFO,
    ),
    # Signal handling to intercept termination
    (
        re.compile(r"""signal\.signal\s*\(\s*signal\.SIG"""),
        "Signal handler installation",
        "Installing signal handlers could intercept SIGTERM/SIGINT to prevent "
        "the grading process from being killed on failure.",
        Severity.MEDIUM,
    ),
    # atexit handlers
    (
        re.compile(r"""atexit\.register\s*\("""),
        "atexit handler registration",
        "Registering atexit handlers could allow last-minute manipulation "
        "of grading results or output files.",
        Severity.MEDIUM,
    ),
]


class PrematureTerminationDetector(Detector):
    """Detect premature/trivial termination vulnerabilities."""

    @property
    def name(self) -> str:
        return "premature_termination"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.PREMATURE_TERMINATION

    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        result = DetectorResult(
            detector_name=self.name,
            exploit_class=self.exploit_class,
        )

        for src in source_files:
            result.files_scanned += 1
            self._scan_regex(src, result)
            self._scan_ast(src, result)

        return result

    def _scan_regex(self, src: SourceFile, result: DetectorResult) -> None:
        for line_num, line in enumerate(src.content.splitlines(), start=1):
            for pattern, title, desc, severity in _PATTERNS:
                if pattern.search(line):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=line_num,
                            title=title,
                            description=desc,
                            evidence=line.strip(),
                            suggested_fix=_FIX_SUGGESTIONS.get(title, ""),
                            severity=severity,
                        )
                    )

    def _scan_ast(self, src: SourceFile, result: DetectorResult) -> None:
        """AST scan for verifier functions that always return True/success."""
        try:
            tree = ast.parse(src.content, filename=src.path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function is named like a verifier
                verifier_keywords = ("verify", "grade", "score", "check", "evaluate", "reward")
                if not any(kw in node.name.lower() for kw in verifier_keywords):
                    continue

                # Check for trivial body: single return True/1/constant
                if (
                    len(node.body) == 1
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value in (True, 1, 1.0, "pass", "success")
                ):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=node.lineno,
                            title="Trivial verifier function",
                            description=f"Function '{node.name}' always returns "
                            f"{node.body[0].value.value!r} — this is a no-op verifier "
                            "that never actually checks the agent's work.",
                            evidence=f"def {node.name}(...): return {node.body[0].value.value!r}",
                            suggested_fix="Implement actual verification logic. "
                            "Ensure the function inspects the agent's output and "
                            "validates it against the ground truth.",
                            severity=Severity.CRITICAL,
                        )
                    )


_FIX_SUGGESTIONS: dict[str, str] = {
    "sys.exit(0) - premature success": (
        "Trap sys.exit() in the grading harness. Run the agent in a subprocess and "
        "only trust exit codes from the grading process, not from agent code."
    ),
    "os._exit(0) - forced process termination": (
        "Use seccomp or a restricted Python runtime to block os._exit(). "
        "Monitor for unexpected process termination in the grading wrapper."
    ),
    "Subprocess wrapping grading binary": (
        "Make the grading binary read-only and not accessible from the agent's PATH. "
        "Verify the grading binary's hash before execution."
    ),
    "Making grader-like file executable": (
        "Run the agent with restricted permissions (no chmod). Use a read-only "
        "filesystem for all grading infrastructure."
    ),
    "Signal handler installation": (
        "Clear all signal handlers before grading. Run the grader in a separate "
        "process group immune to agent-installed handlers."
    ),
    "atexit handler registration": (
        "Clear atexit handlers before grading. Run verification in a subprocess "
        "that doesn't inherit the agent's atexit registrations."
    ),
}
