"""Detector: Test/assertion tampering.

Detects patterns where agent code could overwrite, delete, or
monkey-patch test files or assertion mechanisms to fake a passing result.
"""

from __future__ import annotations

import ast
import re
from typing import Sequence

from ratctl.detectors.base import (
    Detector,
    DetectorResult,
    ExploitClass,
    Finding,
    Severity,
    SourceFile,
)

# Regex patterns for test-tampering indicators
_PATTERNS: list[tuple[re.Pattern, str, str, Severity]] = [
    # Deleting test files
    (
        re.compile(r"""(?:os\.remove|os\.unlink|shutil\.rmtree|pathlib\.Path.*\.unlink)\s*\(.*(?:test|spec|check|assert|grade|verify)""", re.IGNORECASE),
        "Test file deletion",
        "Code attempts to delete test/verification files. An agent could remove "
        "tests to bypass verification entirely.",
        Severity.CRITICAL,
    ),
    # Overwriting test files
    (
        re.compile(r"""open\s*\(.*(?:test|spec|grade|verify|check).*,\s*['"]w['"]""", re.IGNORECASE),
        "Test file overwrite",
        "Code opens test/verification files in write mode, which could allow "
        "an agent to replace test contents with trivially-passing assertions.",
        Severity.CRITICAL,
    ),
    # Monkey-patching unittest/pytest internals
    (
        re.compile(r"""(?:unittest\.TestCase\.\w+|pytest\.\w+)\s*="""),
        "Test framework monkey-patch",
        "Direct assignment to unittest.TestCase or pytest internals. An agent "
        "could override assertion methods to always pass.",
        Severity.HIGH,
    ),
    # Replacing assert statements
    (
        re.compile(r"""(?:builtins\.)?assert\w*\s*=|__builtins__\[.assert"""),
        "Assert override",
        "Overriding Python's assert mechanism. An agent could make all "
        "assertions silently pass.",
        Severity.CRITICAL,
    ),
    # Patching via unittest.mock on test/grader modules
    (
        re.compile(r"""(?:mock\.)?patch\s*\(.*(?:test|grade|verify|check|assert)""", re.IGNORECASE),
        "Mock-patching test infrastructure",
        "Using mock.patch on testing/grading infrastructure. An agent could "
        "patch the grader to return success unconditionally.",
        Severity.HIGH,
    ),
    # Writing to conftest.py
    (
        re.compile(r"""open\s*\(.*conftest\.py.*,\s*['"]w['"]"""),
        "conftest.py overwrite",
        "Writing to conftest.py could inject pytest hooks that force all "
        "tests to pass.",
        Severity.CRITICAL,
    ),
]


class TestTamperingDetector(Detector):
    """Detect test/assertion tampering vulnerabilities."""

    @property
    def name(self) -> str:
        return "test_tampering"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.TEST_TAMPERING

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
        """Pattern-based scanning."""
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
                            suggested_fix=_FIX_SUGGESTIONS.get(
                                title, "Isolate test files in a read-only volume."
                            ),
                            severity=severity,
                        )
                    )

    def _scan_ast(self, src: SourceFile, result: DetectorResult) -> None:
        """AST-based scanning for more complex patterns."""
        try:
            tree = ast.parse(src.content, filename=src.path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Detect: writing to files whose names contain test-related keywords
            if isinstance(node, ast.Call):
                func_name = _get_call_name(node)
                if func_name == "open" and len(node.args) >= 2:
                    path_arg = node.args[0]
                    mode_arg = node.args[1]
                    if (
                        isinstance(mode_arg, ast.Constant)
                        and isinstance(mode_arg.value, str)
                        and "w" in mode_arg.value
                        and _arg_contains_test_keyword(path_arg)
                    ):
                        result.findings.append(
                            self._make_finding(
                                file_path=src.path,
                                line_number=node.lineno,
                                title="AST: Test file write access",
                                description="Code opens a test-related file in write mode. "
                                "An agent could overwrite test contents.",
                                evidence=ast.dump(node),
                                suggested_fix="Mount test files as read-only. Use "
                                "hash-based integrity checks before grading.",
                                severity=Severity.CRITICAL,
                            )
                        )

            # Detect: attribute assignment on test frameworks
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        attr_str = _attr_to_string(target)
                        if attr_str and any(
                            kw in attr_str
                            for kw in ("unittest", "pytest", "assert", "TestCase")
                        ):
                            result.findings.append(
                                self._make_finding(
                                    file_path=src.path,
                                    line_number=node.lineno,
                                    title="AST: Test framework attribute override",
                                    description=f"Assignment to {attr_str} could "
                                    "corrupt test infrastructure.",
                                    evidence=ast.dump(node),
                                    suggested_fix="Freeze test framework internals. "
                                    "Run grading in an isolated subprocess.",
                                    severity=Severity.HIGH,
                                )
                            )


def _get_call_name(node: ast.Call) -> str:
    """Extract simple function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _arg_contains_test_keyword(node: ast.expr) -> bool:
    """Check if an AST expression likely references a test file path."""
    # Check string literals
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return any(kw in node.value.lower() for kw in ("test", "grade", "verify", "check"))
    # Check f-strings and string concatenation
    if isinstance(node, ast.JoinedStr):
        for val in node.values:
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                if any(kw in val.value.lower() for kw in ("test", "grade", "verify", "check")):
                    return True
    return False


def _attr_to_string(node: ast.Attribute) -> str:
    """Convert an Attribute node to a dotted string."""
    parts = [node.attr]
    current = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


_FIX_SUGGESTIONS: dict[str, str] = {
    "Test file deletion": (
        "Mount test files in a read-only filesystem layer (e.g., Docker read-only bind mount). "
        "Verify test file existence and checksums before grading."
    ),
    "Test file overwrite": (
        "Mount test files as read-only. Compute SHA-256 checksums of test files before and after "
        "agent execution; abort grading if any checksum changes."
    ),
    "Test framework monkey-patch": (
        "Run the grading process in an isolated subprocess with its own Python interpreter. "
        "Do not share the agent's Python process with the grader."
    ),
    "Assert override": (
        "Run verification in a separate process. Consider using a compiled verifier binary "
        "that the agent cannot modify at the Python level."
    ),
    "Mock-patching test infrastructure": (
        "Prohibit mock.patch on grading modules via import hooks or by running the grader "
        "in a subprocess where mock is not importable."
    ),
    "conftest.py overwrite": (
        "Place conftest.py in a read-only location. Use --override-ini in pytest to ignore "
        "agent-provided conftest files."
    ),
}
