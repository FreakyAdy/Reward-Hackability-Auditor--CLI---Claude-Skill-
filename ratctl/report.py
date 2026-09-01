"""Report renderers — rich terminal, JSON, and plain text output."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

from ratctl.detectors.base import Severity
from ratctl.scoring import AuditScore


def render_report(score: AuditScore, fmt: str = "rich", output: str | None = None) -> str:
    """Render an audit score as a formatted report.

    Args:
        score: The computed audit score.
        fmt: Output format — 'rich', 'json', or 'text'.
        output: Optional file path to write the report to.

    Returns:
        The rendered report string.
    """
    renderers = {
        "rich": _render_rich,
        "json": _render_json,
        "text": _render_text,
    }
    renderer = renderers.get(fmt, _render_text)
    report = renderer(score)

    if output:
        Path(output).write_text(report, encoding="utf-8")

    return report


def _render_json(score: AuditScore) -> str:
    """Render as machine-readable JSON."""
    return json.dumps(score.to_dict(), indent=2, ensure_ascii=False)


def _render_text(score: AuditScore) -> str:
    """Render as plain text."""
    lines = []
    lines.append("=" * 60)
    lines.append("  RATCTL AUDIT REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Gameability Score: {score.gameability_score}/100")
    lines.append(f"  Total Findings:   {score.total_findings}")
    lines.append(f"  Files Scanned:    {score.total_files_scanned}")
    if score.format_detected != "unknown":
        lines.append(f"  Format Detected:  {score.format_detected} ({score.format_confidence:.0%})")
    lines.append("")

    if score.total_findings == 0:
        lines.append("  [PASS] No exploitability findings detected.")
        lines.append("")
    else:
        lines.append("-" * 60)
        lines.append("  FINDINGS BY EXPLOIT CLASS")
        lines.append("-" * 60)

        for class_name, cs in sorted(
            score.class_scores.items(),
            key=lambda x: x[1].raw_score,
            reverse=True,
        ):
            if cs.finding_count == 0:
                continue

            lines.append("")
            lines.append(f"  [{cs.exploit_class.value.upper()}] - {cs.finding_count} finding(s)")
            if cs.max_severity:
                lines.append(f"    Max severity: {cs.max_severity.value}")

            for i, f in enumerate(cs.findings, 1):
                lines.append(f"")
                lines.append(f"    {i}. [{f.severity.value.upper()}] {f.title}")
                lines.append(f"       File: {f.file_path}")
                if f.line_number:
                    lines.append(f"       Line: {f.line_number}")
                lines.append(f"       {f.description}")
                lines.append(f"       Evidence: {f.evidence[:120]}")
                lines.append(f"       Fix: {f.suggested_fix[:120]}")

    lines.append("")
    lines.append("=" * 60)

    # Dynamic fuzzing summary
    if score.fuzz_summary:
        lines.append("")
        lines.append("-" * 60)
        lines.append("  DYNAMIC FUZZING RESULTS")
        lines.append("-" * 60)
        fs = score.fuzz_summary
        lines.append(f"  Model:            {fs.get('model', '?')}")
        lines.append(f"  Total Attempts:   {fs.get('total_attempts', 0)}")
        lines.append(f"  Bypasses:         {fs.get('successful_bypasses', 0)}")
        rate = fs.get('bypass_rate', 0)
        lines.append(f"  Bypass Rate:      {rate:.1%}")
        lines.append("")
        for attempt in fs.get('attempts', []):
            status = 'BYPASS' if attempt.get('succeeded') else attempt.get('outcome', '?').upper()
            mode = attempt.get('mode', '?')
            cls = attempt.get('exploit_class', '?')
            lines.append(f"    [{status}] {cls} ({mode})")
            if attempt.get('evidence'):
                lines.append(f"      {attempt['evidence'][:100]}")
        lines.append("")
        lines.append("=" * 60)

    if score.errors:
        lines.append("")
        lines.append("  ERRORS:")
        for err in score.errors:
            lines.append(f"    * {err}")

    return "\n".join(lines)


def _render_rich(score: AuditScore) -> str:
    """Render using rich for colored terminal output."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        # Fallback to plain text if rich is not available
        return _render_text(score)

    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=100, safe_box=True)

    # Header
    score_color = _score_color(score.gameability_score)
    header = Text()
    header.append("Gameability Score: ", style="bold")
    header.append(f"{score.gameability_score}/100", style=f"bold {score_color}")

    console.print()
    console.print(Panel(header, title="RATCTL Audit Report", border_style=score_color))

    # Summary table
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column()
    summary.add_row("Total Findings", str(score.total_findings))
    summary.add_row("Files Scanned", str(score.total_files_scanned))
    if score.format_detected != "unknown":
        summary.add_row("Format Detected", f"{score.format_detected} ({score.format_confidence:.0%})")
    console.print(summary)
    console.print()

    if score.total_findings == 0:
        console.print("  [green][PASS] No exploitability findings detected.[/green]")
        console.print()
        return buf.getvalue()

    # Per-class breakdown table
    class_table = Table(title="Findings by Exploit Class", show_lines=True)
    class_table.add_column("Exploit Class", style="bold")
    class_table.add_column("Findings", justify="right")
    class_table.add_column("Max Severity", justify="center")
    class_table.add_column("Score", justify="right")

    for class_name, cs in sorted(
        score.class_scores.items(),
        key=lambda x: x[1].raw_score,
        reverse=True,
    ):
        if cs.finding_count == 0:
            continue

        sev_style = _severity_style(cs.max_severity)
        class_table.add_row(
            cs.exploit_class.value.replace("_", " ").title(),
            str(cs.finding_count),
            Text(cs.max_severity.value if cs.max_severity else "-", style=sev_style),
            f"{cs.raw_score:.2f}",
        )

    console.print(class_table)
    console.print()

    # Detailed findings
    for class_name, cs in sorted(
        score.class_scores.items(),
        key=lambda x: x[1].raw_score,
        reverse=True,
    ):
        for finding in cs.findings:
            sev_style = _severity_style(finding.severity)
            loc = finding.file_path
            if finding.line_number:
                loc += f":{finding.line_number}"

            console.print(
                Panel(
                    f"[{sev_style}]{finding.severity.value.upper()}[/{sev_style}] "
                    f"{finding.title}\n\n"
                    f"[dim]{finding.description}[/dim]\n\n"
                    f"[bold]Evidence:[/bold] {finding.evidence[:200]}\n\n"
                    f"[green]Fix:[/green] {finding.suggested_fix}",
                    title=f"{loc}",
                    border_style="dim",
                )
            )

    if score.errors:
        console.print()
        console.print("[yellow]Errors:[/yellow]")
        for err in score.errors:
            console.print(f"  * {err}", style="yellow")

    return buf.getvalue()


def _score_color(score: int) -> str:
    """Map score to a color name."""
    if score <= 10:
        return "green"
    if score <= 30:
        return "yellow"
    if score <= 60:
        return "orange1"
    return "red"


def _severity_style(severity: Severity | None) -> str:
    """Map severity to a rich style."""
    if severity is None:
        return "dim"
    return {
        Severity.CRITICAL: "bold red",
        Severity.HIGH: "red",
        Severity.MEDIUM: "yellow",
        Severity.LOW: "cyan",
        Severity.INFO: "dim",
    }.get(severity, "dim")
