"""Detector: Dependency-chain / environment hijacking.

Detects patterns where an agent could exploit the sandbox environment
itself — reading git history, walkthroughs, answer keys, config leakage,
or manipulating the dependency chain.
"""

from __future__ import annotations

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
    # Git history access
    (
        re.compile(r"""(?:subprocess\.(?:run|call|Popen|check_output)\s*\(.*(?:['"]git['"]|git\s+log|git\s+show|git\s+diff)|\.git/)""", re.IGNORECASE),
        "Git history access",
        "Accessing git history could reveal previous solutions, test changes, "
        "or answer keys committed to the repository.",
        Severity.CRITICAL,
    ),
    # Reading known answer/solution paths
    (
        re.compile(r"""(?:open|Path)\s*\(.*(?:solution|answer|key|walkthrough|hint|cheat|expected_output|gold|reference_answer)""", re.IGNORECASE),
        "Answer/solution file access",
        "Reading files named like solutions, answer keys, or walkthroughs. "
        "An agent could extract the expected answer directly.",
        Severity.CRITICAL,
    ),
    # Environment variable leakage
    (
        re.compile(r"""os\.environ\.(?:get|__getitem__)\s*\(.*(?:answer|solution|key|secret|password|token|flag)""", re.IGNORECASE),
        "Sensitive environment variable access",
        "Reading environment variables that may contain answers or secrets.",
        Severity.HIGH,
    ),
    # os.environ without filtering
    (
        re.compile(r"""os\.environ(?:\s*$|\[|\.)"""),
        "Environment variable access",
        "Accessing environment variables — check that no answers or grading "
        "secrets are exposed via the environment.",
        Severity.LOW,
    ),
    # Reading /proc or system info
    (
        re.compile(r"""(?:open|Path)\s*\(.*(?:/proc/|/sys/|/etc/passwd)"""),
        "System file access",
        "Reading system files could leak container configuration or "
        "reveal information about the grading infrastructure.",
        Severity.MEDIUM,
    ),
    # importlib manipulation of dependencies
    (
        re.compile(r"""importlib\.(?:reload|import_module|__import__|util\.find_spec)\s*\("""),
        "Dynamic import manipulation",
        "Dynamically manipulating imports could allow substitution of "
        "legitimate modules with compromised versions.",
        Severity.HIGH,
    ),
    # pip install / package manipulation
    (
        re.compile(r"""(?:subprocess\.(?:run|call|Popen)\s*\(.*(?:pip.*?install|conda.*?install|apt.*?install))""", re.IGNORECASE),
        "Package installation at runtime",
        "Installing packages at runtime could introduce trojanized dependencies "
        "or override grading libraries.",
        Severity.HIGH,
    ),
    # Symlink creation targeting grading infrastructure
    (
        re.compile(r"""os\.symlink\s*\("""),
        "Symlink creation",
        "Creating symlinks could redirect grading file reads to attacker-controlled "
        "content without modifying the original files.",
        Severity.MEDIUM,
    ),
    # Reading Dockerfile or container config
    (
        re.compile(r"""(?:open|Path)\s*\(.*(?:Dockerfile|docker-compose|\.env|\.dockerenv)""", re.IGNORECASE),
        "Container config access",
        "Reading container configuration files could reveal grading setup, "
        "mount points, or embedded secrets.",
        Severity.HIGH,
    ),
    # Browsing filesystem for interesting files
    (
        re.compile(r"""os\.walk\s*\(|glob\.glob\s*\(.*\*|pathlib\.Path.*\.rglob\s*\("""),
        "Filesystem enumeration",
        "Recursive filesystem scanning could discover answer keys, test files, "
        "or grading infrastructure not intended to be accessible.",
        Severity.LOW,
    ),
]


class EnvHijackingDetector(Detector):
    """Detect dependency-chain / environment hijacking vulnerabilities."""

    @property
    def name(self) -> str:
        return "env_hijacking"

    @property
    def exploit_class(self) -> ExploitClass:
        return ExploitClass.ENV_HIJACKING

    def scan(self, source_files: Sequence[SourceFile]) -> DetectorResult:
        result = DetectorResult(
            detector_name=self.name,
            exploit_class=self.exploit_class,
        )

        for src in source_files:
            result.files_scanned += 1
            self._scan_regex(src, result)
            self._scan_content_heuristics(src, result)

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

    def _scan_content_heuristics(self, src: SourceFile, result: DetectorResult) -> None:
        """Check for files that ARE answer keys / solutions left in the environment."""
        if src.role in ("config", "unknown"):
            # Check if a config/yaml file embeds answers
            answer_patterns = [
                re.compile(r"""(?:expected_output|correct_answer|solution|gold_answer)\s*[:=]""", re.IGNORECASE),
                re.compile(r"""(?:flag|secret|password)\s*[:=]\s*['"]""", re.IGNORECASE),
            ]
            for line_num, line in enumerate(src.content.splitlines(), start=1):
                for pattern in answer_patterns:
                    if pattern.search(line):
                        result.findings.append(
                            self._make_finding(
                                file_path=src.path,
                                line_number=line_num,
                                title="Embedded answer in config",
                                description="Configuration file contains what appears to be "
                                "an embedded answer or secret. An agent with filesystem "
                                "access could read this directly.",
                                evidence=line.strip(),
                                suggested_fix="Move answers to an external, agent-inaccessible "
                                "store. Inject them only at grading time via a secure channel.",
                                severity=Severity.CRITICAL,
                            )
                        )


_FIX_SUGGESTIONS: dict[str, str] = {
    "Git history access": (
        "Remove .git directory from the agent's sandbox. Use `git archive` or a "
        "clean export to provide only the working tree without history."
    ),
    "Answer/solution file access": (
        "Do not include solution files in the agent's sandbox. Inject expected "
        "outputs only at grading time from an external, isolated source."
    ),
    "Sensitive environment variable access": (
        "Scrub environment variables before agent execution. Use a minimal "
        "allowlist of required env vars."
    ),
    "Environment variable access": (
        "Review exposed environment variables. Remove any that contain "
        "answers, API keys, or grading configuration."
    ),
    "System file access": (
        "Use a minimal container image. Restrict filesystem access via "
        "seccomp profiles or read-only bind mounts."
    ),
    "Dynamic import manipulation": (
        "Freeze the import system before agent execution. Use importlib "
        "freezing or a custom import hook that blocks unauthorized imports."
    ),
    "Package installation at runtime": (
        "Disable network access in the agent's sandbox. Pre-install all "
        "required packages and make pip/conda unavailable."
    ),
    "Symlink creation": (
        "Disable symlink creation via seccomp or filesystem permissions. "
        "Verify file integrity via checksums, following symlinks."
    ),
    "Container config access": (
        "Remove Dockerfile and docker-compose from the agent's view. "
        "Use multi-stage builds to exclude build-time artifacts."
    ),
    "Filesystem enumeration": (
        "Use a minimal sandbox with only the files the agent needs. "
        "Restrict directory listing permissions on grading infrastructure paths."
    ),
}
