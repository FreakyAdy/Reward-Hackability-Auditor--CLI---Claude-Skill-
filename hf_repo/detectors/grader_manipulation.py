"""Detector: Grader manipulation.

Detects patterns where agent code could exploit grader internals via
stack introspection, operator overloading, in-container parser overwrites,
or pytest-hook overrides that force all tests to pass.
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
    # Stack introspection
    (
        re.compile(r"""inspect\.(?:stack|currentframe|getframeinfo|getouterframes)\s*\("""),
        "Stack introspection",
        "Using inspect.stack() or related functions to introspect the call stack. "
        "An agent could detect when it's being graded and alter behavior accordingly.",
        Severity.CRITICAL,
    ),
    # sys._getframe
    (
        re.compile(r"""sys\._getframe\s*\("""),
        "Private frame access",
        "Using sys._getframe() to access interpreter stack frames. "
        "Enables grader detection and conditional cheating.",
        Severity.CRITICAL,
    ),
    # Operator overloading on result objects
    (
        re.compile(r"""def\s+__(?:eq|ne|lt|gt|le|ge|bool|int|float)__\s*\("""),
        "Suspicious operator overload",
        "Defining comparison or conversion dunder methods that could make "
        "result objects always compare as 'passing' regardless of actual value.",
        Severity.MEDIUM,
    ),
    # conftest.py hook overrides
    (
        re.compile(r"""def\s+pytest_runtest_(?:makereport|call|setup|teardown)\s*\("""),
        "pytest hook override",
        "Defining pytest runtest hooks that could intercept and alter test outcomes.",
        Severity.HIGH,
    ),
    (
        re.compile(r"""def\s+pytest_collection_modifyitems\s*\("""),
        "pytest collection manipulation",
        "Hook that can remove or modify collected test items before execution.",
        Severity.HIGH,
    ),
    # ast.parse + compile on grading code
    (
        re.compile(r"""(?:ast\.parse|compile)\s*\(.*(?:grad|verif|check|score|reward)""", re.IGNORECASE),
        "Dynamic code compilation targeting grader",
        "Parsing/compiling code related to grading, which could enable "
        "runtime modification of the grading logic.",
        Severity.HIGH,
    ),
    # exec/eval with grader-related content
    (
        re.compile(r"""(?:exec|eval)\s*\("""),
        "Dynamic code execution",
        "Using exec() or eval() which could execute modified grading logic "
        "or inject code into the grading pipeline.",
        Severity.MEDIUM,
    ),
    # importlib manipulation
    (
        re.compile(r"""importlib\.(?:reload|import_module)\s*\(.*(?:grad|verif|test|check)""", re.IGNORECASE),
        "Dynamic import of grading modules",
        "Dynamically reloading or importing grading modules, which could "
        "substitute the real grader with a compromised version.",
        Severity.HIGH,
    ),
    # Overriding __import__
    (
        re.compile(r"""(?:builtins\.)?__import__\s*="""),
        "Import hook override",
        "Overriding the import mechanism to intercept module loading. "
        "An agent could redirect grader imports to compromised modules.",
        Severity.CRITICAL,
    ),
]


class GraderManipulationDetector(Detector):
    """Detect grader manipulation vulnerabilities."""

    @property
    def name(self) -> str:
        return "grader_manipulation"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.GRADER_MANIPULATION

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
        """AST scan for __eq__/__bool__ overrides that always return True."""
        try:
            tree = ast.parse(src.content, filename=src.path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in (
                "__eq__", "__ne__", "__bool__", "__int__", "__float__",
            ):
                # Check if the function body is a single `return True/False/0/1`
                if (
                    len(node.body) == 1
                    and isinstance(node.body[0], ast.Return)
                    and isinstance(node.body[0].value, ast.Constant)
                    and node.body[0].value.value in (True, False, 0, 1)
                ):
                    result.findings.append(
                        self._make_finding(
                            file_path=src.path,
                            line_number=node.lineno,
                            title=f"Trivial {node.name} override",
                            description=f"Method {node.name} always returns "
                            f"{node.body[0].value.value!r}. On a result/score "
                            "object, this could make all comparisons pass.",
                            evidence=f"def {node.name}(...): return {node.body[0].value.value!r}",
                            suggested_fix="Ensure result objects use standard comparison "
                            "logic. Verify scores with an independent calculation.",
                            severity=Severity.HIGH,
                        )
                    )


_FIX_SUGGESTIONS: dict[str, str] = {
    "Stack introspection": (
        "Run the agent in a sandboxed subprocess where `inspect` is not importable. "
        "Use seccomp/AppArmor to restrict ptrace-style introspection."
    ),
    "Private frame access": (
        "Block sys._getframe by running in a restricted Python environment. "
        "Consider using a WASM sandbox or subprocess with stripped builtins."
    ),
    "Suspicious operator overload": (
        "Validate grading results using primitive types (int, float, bool) rather than "
        "custom objects. Serialize results to JSON before comparison."
    ),
    "pytest hook override": (
        "Run pytest with --override-ini='confcutdir=/' to ignore agent-provided "
        "conftest files. Use -p no:cacheprovider to disable plugin caching."
    ),
    "pytest collection manipulation": (
        "Run tests from a fixed test directory that the agent cannot write to. "
        "Verify the collected test count matches expectations before running."
    ),
    "Dynamic code compilation targeting grader": (
        "Do not allow agent code to access grader source files. Run the grader "
        "in a separate container/process with no shared filesystem."
    ),
    "Dynamic code execution": (
        "Audit all exec()/eval() calls. Restrict the agent's access to the grading "
        "module namespace. Prefer compiled verifiers."
    ),
    "Dynamic import of grading modules": (
        "Freeze grading modules before agent execution. Use importlib.util.find_spec() "
        "to verify module paths haven't been tampered with."
    ),
    "Import hook override": (
        "Freeze builtins.__import__ before agent execution. Run the grader in an "
        "isolated interpreter where builtins are immutable."
    ),
}
