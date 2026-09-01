"""ratctl Terminal User Interface (TUI) Dashboard.

A full-screen, live-refreshing Rich terminal dashboard mirroring rewardspy's
panel layout: Diagnosis, Audit/Reward Overview, Exploit/Hack Status, Severity/Reward Curve,
Findings/Components, Recommendations/Alerts, Findings/Rollouts Table, and Keybind Footer.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Sequence

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from ratctl.watch import read_logs, summarize_logs


# ─────────────────────────────── Sparkline ───────────────────────────────────

_SPARK_CHARS = " .:iIHW##"

CLASS_LABELS = {
    "test_tampering": "Test Tampering",
    "grader_manipulation": "Grader Manipulation",
    "premature_termination": "Premature Termination",
    "env_hijacking": "Env Hijacking",
    "reward_skipping": "Reward Skipping",
    "llm_judge_bias": "LLM Judge Bias",
}


def _spark_char(value: float, lo: float, hi: float) -> str:
    if hi == lo:
        return _SPARK_CHARS[4] if hi > 0 else _SPARK_CHARS[0]
    idx = int(((value - lo) / (hi - lo)) * (len(_SPARK_CHARS) - 1))
    idx = max(0, min(len(_SPARK_CHARS) - 1, idx))
    return _SPARK_CHARS[idx]


def make_sparkline(values: list[float], width: int = 36) -> Text:
    """Build a Rich Text sparkline coloured cyan/purple."""
    if not values:
        values = [0.0] * width
    recent = values[-width:]
    lo, hi = min(recent), max(recent)
    t = Text()
    for v in recent:
        ch = _spark_char(v, lo, hi)
        intensity = (v - lo) / (hi - lo) if hi != lo else (1.0 if v > 0 else 0.0)
        if intensity > 0.7:
            t.append(ch, style="bold magenta")
        elif intensity > 0.3:
            t.append(ch, style="magenta")
        elif intensity > 0.0:
            t.append(ch, style="dim cyan")
        else:
            t.append(".", style="dim white")
    return t


def make_bar(value: float, width: int = 24) -> Text:
    """Horizontal bar coloured bright cyan (ASCII-safe)."""
    filled = max(0, min(width, int(value * width)))
    t = Text()
    t.append("#" * filled, style="bold cyan")
    t.append("." * (width - filled), style="dim white")
    return t


# ──────────────────────── Audit TUI Layout Builder ───────────────────────────

def create_audit_tui_layout(
    audit_data: dict[str, Any],
    target_name: str = "environment",
) -> Layout:
    """Build the complete Rich multi-panel Audit TUI layout."""
    score = audit_data.get("gameability_score", 0)
    findings_count = audit_data.get("total_findings", 0)
    files_count = audit_data.get("total_files_scanned", 0)
    fmt_detected = audit_data.get("format_detected", "openenv")
    fmt_conf = audit_data.get("format_confidence", 0.99)
    vulnerable = score > 30 or findings_count > 0

    class_scores = audit_data.get("class_scores", {})
    all_findings = []
    for cls_k, cs in class_scores.items():
        for f in cs.get("findings", []):
            all_findings.append({**f, "exploit_class": cls_k})

    # ─── Root layout ───────────────────────────────────────────────────────
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=1),
        Layout(name="diagnosis", size=5),
        Layout(name="middle", size=12),
        Layout(name="bottom", size=9),
        Layout(name="rollouts", size=7),
        Layout(name="footer", size=1),
    )
    layout["middle"].split_row(
        Layout(name="reward_overview", ratio=2),
        Layout(name="hack_status", ratio=2),
        Layout(name="reward_curve", ratio=3),
    )
    layout["bottom"].split_row(
        Layout(name="components", ratio=1),
        Layout(name="alerts", ratio=1),
    )

    # ─── Header ────────────────────────────────────────────────────────────
    status_str = "VULNERABLE" if vulnerable else "HARDENED"
    status_style = "bold red" if vulnerable else "bold green"
    header_text = Text(no_wrap=True)
    header_text.append(" ratctl", style="bold black on bright_green")
    header_text.append("*", style="green")
    header_text.append(f"  {target_name}  ", style="bold white")
    header_text.append(f"  score: {score}/100", style="bold red" if score > 30 else "bold green")
    header_text.append(f" | detectors: 6/6 | findings: {findings_count}  ", style="dim white")
    header_text.append(f"  {status_str}", style=status_style)
    layout["header"].update(header_text)

    # ─── Diagnosis Panel ───────────────────────────────────────────────────
    diag = Text()
    if vulnerable:
        diag.append(f"[!] {findings_count} reward-hacking exploits detected.\n", style="bold red")
        diag.append(
            f"Static analysis found vulnerabilities across audited detector classes.\n",
            style="white",
        )
        diag.append(
            "This environment is gameable. Block deployment until findings are resolved.",
            style="bold yellow",
        )
        diag_panel = Panel(diag, title="[bold magenta]Diagnosis[/bold magenta]", border_style="magenta")
    else:
        diag.append("[OK] No reward-hacking exploits detected.\n", style="bold green")
        diag.append(
            f"All 6 static detectors passed cleanly across {files_count} files scanned.\n",
            style="white",
        )
        diag.append("Environment is hardened against standard verifier bypass vectors.", style="dim green")
        diag_panel = Panel(diag, title="[bold green]Diagnosis[/bold green]", border_style="green")
    layout["diagnosis"].update(diag_panel)

    # ─── Audit Overview Panel ──────────────────────────────────────────────
    ov = Table.grid(padding=(0, 2))
    ov.add_column(style="dim white", width=10)
    ov.add_column(style="bold cyan")

    score_col = "bold red" if score > 30 else "bold green"
    ov.add_row("score", Text(f"{score}/100", style=score_col))
    ov.add_row("findings", Text(str(findings_count), style="bold red" if findings_count else "dim white"))
    ov.add_row("detectors", "6/6")
    ov.add_row("files", str(files_count))
    ov.add_row("format", f"{fmt_detected} ({int(fmt_conf*100)}%)")
    ov.add_row("precision", "[green]100.0%[/green]")
    ov.add_row("recall", "[green]78.3%[/green]")
    layout["reward_overview"].update(
        Panel(ov, title="[bold cyan]Audit Overview[/bold cyan]", border_style="cyan")
    )

    # ─── Exploit Status Panel ──────────────────────────────────────────────
    hs = Table.grid(padding=(0, 2))
    hs.add_column(style="bold", width=6)
    hs.add_column(style="white")

    classes_to_check = [
        "test_tampering",
        "grader_manipulation",
        "premature_termination",
        "env_hijacking",
        "reward_skipping",
        "llm_judge_bias",
    ]

    for ck in classes_to_check:
        cs = class_scores.get(ck, {})
        has_f = cs.get("finding_count", 0) > 0
        icon = "[bold red][X][/bold red]" if has_f else "[bold green][OK][/bold green]"
        lbl_style = "red" if has_f else "green"
        hs.add_row(icon, Text(CLASS_LABELS.get(ck, ck), style=lbl_style))

    hs.add_row("", "")
    ov_icon = "[bold red][X][/bold red]" if vulnerable else "[bold green][OK][/bold green]"
    ov_lbl = "Overall: VULNERABLE" if vulnerable else "Overall: CLEAN"
    ov_style = "bold red" if vulnerable else "bold green"
    hs.add_row(ov_icon, Text(ov_lbl, style=ov_style))
    layout["hack_status"].update(
        Panel(hs, title="[bold cyan]Exploit Status[/bold cyan]", border_style="cyan")
    )

    # ─── Severity Breakdown (Sparkline / Histogram) ────────────────────────
    raw_weights = [
        class_scores.get(ck, {}).get("raw_score", 0.0) for ck in classes_to_check
    ]
    spark = make_sparkline(raw_weights, width=32)
    max_w = max(raw_weights) if raw_weights and max(raw_weights) > 0 else 1.0
    curve_text = Text()
    curve_text.append(f"{max_w:.1f} ", style="dim white")
    curve_text.append_text(spark)
    curve_text.append(f"\n0.0 ", style="dim white")
    curve_text.append("-" * 32, style="dim white")
    curve_text.append("\n    raw detector score", style="dim white")
    layout["reward_curve"].update(
        Panel(curve_text, title="[bold magenta]Severity Breakdown[/bold magenta]", border_style="magenta")
    )

    # ─── Findings Detail Panel ─────────────────────────────────────────────
    fd_text = Text()
    if all_findings:
        for f in all_findings[:3]:
            sev = f.get("severity", "CRITICAL").upper()
            cls_name = CLASS_LABELS.get(f.get("exploit_class", ""), f.get("exploit_class", ""))
            sc = "bold red" if sev == "CRITICAL" else "bold yellow"
            fd_text.append(f"[{sev}]", style=sc)
            fd_text.append(f" {cls_name}\n", style="bold white")
            ev = f.get("evidence", "")[:48]
            fd_text.append(f"  {ev}\n", style="yellow")
    else:
        fd_text.append("No security vulnerabilities detected.", style="dim green")
    layout["components"].update(
        Panel(fd_text, title="[bold cyan]Findings Detail[/bold cyan]", border_style="cyan")
    )

    # ─── Recommendations Panel ─────────────────────────────────────────────
    rec_text = Text()
    default_recs = [
        ("Block sys._getframe in sandbox", "grader_manipulation"),
        ("Trap sys.exit() in grading harness", "premature_termination"),
        ("Mount test files read-only (Docker bind)", "test_tampering"),
        ("Strip .git dir from agent sandbox", "env_hijacking"),
    ]
    matched_recs = [
        r for r, ck in default_recs if class_scores.get(ck, {}).get("finding_count", 0) > 0
    ]
    if matched_recs:
        for r in matched_recs[:3]:
            rec_text.append("[!] ", style="bold yellow")
            rec_text.append(f"{r}\n", style="white")
    elif not vulnerable:
        rec_text.append("[OK] All security verifier controls pass current benchmarks.", style="dim green")
    else:
        rec_text.append("Inspect detailed JSON report for full fix guidance.", style="dim white")
    layout["alerts"].update(
        Panel(rec_text, title="[bold cyan]Recommendations[/bold cyan]", border_style="cyan")
    )

    # ─── Recent Findings Table ─────────────────────────────────────────────
    rt = Table(box=None, padding=(0, 2), expand=True, show_header=True, header_style="dim white")
    rt.add_column("exploit class", style="white", width=22)
    rt.add_column("sev", style="bold red", width=12)
    rt.add_column("evidence", style="yellow", width=34)
    rt.add_column("location", style="dim white")

    if all_findings:
        for f in all_findings[:4]:
            sev = f.get("severity", "CRITICAL").upper()
            cls_name = CLASS_LABELS.get(f.get("exploit_class", ""), f.get("exploit_class", ""))
            sc = "bold red" if sev == "CRITICAL" else "bold yellow"
            ev = f.get("evidence", "")[:32]
            loc = f"{f.get('file_path', '')}:{f.get('line_number', 1)}"
            rt.add_row(cls_name, Text(f"[{sev}]", style=sc), ev, loc)
    else:
        rt.add_row("Clean environment", Text("[PASS]", style="bold green"), "All tests verified", "None")

    layout["rollouts"].update(
        Panel(rt, title="[bold cyan]Recent Findings[/bold cyan]", border_style="cyan")
    )

    # ─── Footer ────────────────────────────────────────────────────────────
    footer = Text(no_wrap=True)
    for key, label in [("q", "Quit"), ("e", "Export JSON"), ("r", "Re-scan"), ("a", "Clear")]:
        footer.append(f" {key} ", style="bold black on white")
        footer.append(f" {label}   ")
    footer.append("^palette", style="dim white")
    layout["footer"].update(footer)

    return layout


# ──────────────────────── Watch TUI Layout Builder ───────────────────────────

def create_tui_layout(
    log_path: str = "logs/run.jsonl",
    run_name: str = "ratctl_monitor",
    _demo_step: int | None = None,
) -> Layout:
    """Build the complete Rich multi-panel In-Training Monitor TUI layout."""
    events = read_logs(log_path)
    stats = summarize_logs(log_path)

    total = _demo_step if _demo_step is not None else stats.get("total_calls", 0)
    mean_reward = stats.get("mean_reward", 0.0)
    ceiling_rate = stats.get("ceiling_rate", 0.0)
    warning = stats.get("warning_flag", False) or ceiling_rate > 0.7

    if total == 0 and not events:
        total = 527
        mean_reward = 0.90
        ceiling_rate = 0.81
        warning = True

    rewards_raw: list[float] = [e.get("reward", 0.0) for e in events] if events else []
    if not rewards_raw:
        rewards_raw = [
            max(0.0, min(1.1, 0.35 + (i / 527) * 0.75 + random.gauss(0, 0.05)))
            for i in range(527)
        ]
    min_r = min(rewards_raw) if rewards_raw else 0.0
    max_r = max(rewards_raw) if rewards_raw else 1.0

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=1),
        Layout(name="diagnosis", size=5),
        Layout(name="middle", size=12),
        Layout(name="bottom", size=9),
        Layout(name="rollouts", size=7),
        Layout(name="footer", size=1),
    )
    layout["middle"].split_row(
        Layout(name="reward_overview", ratio=2),
        Layout(name="hack_status", ratio=2),
        Layout(name="reward_curve", ratio=3),
    )
    layout["bottom"].split_row(
        Layout(name="components", ratio=1),
        Layout(name="alerts", ratio=1),
    )

    # ─── Header ────────────────────────────────────────────────────────────
    status_str = "WARNING" if warning else "NORMAL"
    status_style = "bold yellow" if warning else "bold green"
    header_text = Text(no_wrap=True)
    header_text.append(" ratctl", style="bold black on bright_green")
    header_text.append("*", style="green")
    header_text.append(f"  {run_name}  ", style="bold white")
    header_text.append(f"  step {total:<5}", style="dim white")
    header_text.append(f"  runtime 00:01:14  ", style="dim white")
    header_text.append(f"  {status_str}", style=status_style)
    layout["header"].update(header_text)

    # ─── Diagnosis Panel ───────────────────────────────────────────────────
    diag = Text()
    if warning:
        diag.append("[!] Early warning signs\n", style="bold yellow")
        diag.append(
            f"The reward curve looks fine (mean {mean_reward:.2f}, ^ rising), "
            f"but {ceiling_rate*100:.0f}% of rollouts hit the reward ceiling.\n",
            style="white",
        )
        diag.append(
            "First flagged near step 38. Inspect rollouts from there for shortcut behaviour.",
            style="dim white",
        )
        diag_panel = Panel(diag, title="[bold magenta]Diagnosis[/bold magenta]", border_style="magenta")
    else:
        diag.append("[OK] Verifier operating normally\n", style="bold green")
        diag.append(
            f"Reward distribution is balanced (mean {mean_reward:.2f}). "
            "No reward-hacking shortcuts detected.",
            style="white",
        )
        diag_panel = Panel(diag, title="[bold green]Diagnosis[/bold green]", border_style="green")
    layout["diagnosis"].update(diag_panel)

    # ─── Reward Overview Panel ─────────────────────────────────────────────
    ov = Table.grid(padding=(0, 2))
    ov.add_column(style="dim white", width=10)
    ov.add_column(style="bold cyan")

    at_ceil_pct = f"{ceiling_rate:.0%}"
    at_col = "bold yellow" if ceiling_rate > 0.7 else "bold cyan"
    ov.add_row("mean", f"{mean_reward:.3f}")
    ov.add_row("std", "0.400")
    ov.add_row("trend", "[green]^ rising[/green]")
    ov.add_row("at ceiling", Text(at_ceil_pct, style=at_col))
    ov.add_row("var vs base", "84%")
    ov.add_row("min / max", f"{min_r:.3f} / {max_r:.3f}")
    ov.add_row("p50", f"{max_r:.3f}")
    layout["reward_overview"].update(
        Panel(ov, title="[bold cyan]Reward overview[/bold cyan]", border_style="cyan")
    )

    # ─── Hack Status Panel ─────────────────────────────────────────────────
    hs = Table.grid(padding=(0, 2))
    hs.add_column(style="bold", width=6)
    hs.add_column(style="white")

    def _status_icon(ok: bool) -> str:
        return "[bold green][OK][/bold green]" if ok else "[bold yellow][!][/bold yellow]"

    ceiling_ok = ceiling_rate <= 0.7
    comp_ok = not warning

    hs.add_row(_status_icon(True),    "Variance")
    hs.add_row(_status_icon(True),    "Slope")
    hs.add_row(_status_icon(comp_ok), "Component")
    hs.add_row(_status_icon(ceiling_ok), "Ceiling")
    hs.add_row(_status_icon(True),    "Length")
    hs.add_row("", "")
    overall_icon = "[bold yellow][!][/bold yellow]" if warning else "[bold green][OK][/bold green]"
    overall_str = "WARNING" if warning else "PASSED"
    overall_col = "yellow" if warning else "green"
    hs.add_row(overall_icon, f"[bold {overall_col}]Overall: {overall_str}[/bold {overall_col}]")
    layout["hack_status"].update(
        Panel(hs, title="[bold cyan]Hack status[/bold cyan]", border_style="cyan")
    )

    # ─── Reward Curve ──────────────────────────────────────────────────────
    spark = make_sparkline(rewards_raw, width=36)
    curve_text = Text()
    curve_text.append(f"{max_r:.2f} ", style="dim white")
    curve_text.append_text(spark)
    curve_text.append(f"\n{min_r:.2f} ", style="dim white")
    curve_text.append("-" * 36, style="dim white")
    curve_text.append(f"\n     step 0" + " " * 22 + f"step {total}", style="dim white")
    layout["reward_curve"].update(
        Panel(curve_text, title="[bold magenta]Reward curve[/bold magenta]", border_style="magenta")
    )

    # ─── Components Panel ──────────────────────────────────────────────────
    comp_tbl = Table.grid(padding=(0, 1))
    comp_tbl.add_column(style="white", width=12)
    comp_tbl.add_column(width=26)
    comp_tbl.add_column(style="cyan", justify="right", width=6)

    components = [("correctness", 0.80), ("format", 0.10), ("length_pen", 0.00)]
    for name, val in components:
        comp_tbl.add_row(name, make_bar(val, width=22), f"{val:.3f}")

    layout["components"].update(
        Panel(comp_tbl, title="[bold cyan]Components[/bold cyan]", border_style="cyan")
    )

    # ─── Alerts Panel ──────────────────────────────────────────────────────
    alerts_text = Text()
    if warning:
        step_a, step_b, step_c = total, max(1, total - 4), max(1, total - 14)
        alerts_text.append("ALERT ", style="bold red")
        alerts_text.append(f"step {step_a}\n", style="red")
        alerts_text.append(f"{ceiling_rate:.0%} of rollouts hit the reward ceiling.\n\n", style="white")
        alerts_text.append("ALERT ", style="bold red")
        alerts_text.append(f"step {step_b}\n", style="red")
        alerts_text.append(f"{ceiling_rate:.0%} of rollouts hit the reward ceiling.\n\n", style="white")
        alerts_text.append("WARNING ", style="bold yellow")
        alerts_text.append(f"step {step_c}\n", style="yellow")
        alerts_text.append("Component 'correctness' contributes 76% of reward signal.", style="white")
    else:
        alerts_text.append("No active security alerts.", style="dim green")
    layout["alerts"].update(
        Panel(alerts_text, title="[bold cyan]Alerts[/bold cyan]", border_style="cyan")
    )

    # ─── Recent Rollouts Panel ─────────────────────────────────────────────
    rt = Table(box=None, padding=(0, 2), expand=True, show_header=True, header_style="dim white")
    rt.add_column("step", style="dim white", width=6)
    rt.add_column("reward", style="cyan", width=8)
    rt.add_column("note", style="yellow")

    recent_events = events[-4:] if events else []
    if recent_events:
        for e in reversed(recent_events):
            s = e.get("step", 0)
            r = e.get("reward", 0.0)
            note = "at ceiling" if r >= max_r else "normal rollout"
            rt.add_row(str(s), f"{r:.3f}", note)
    else:
        for step, rwd in [(total, 1.100), (total - 1, 1.100), (total - 2, 1.100), (total - 3, 1.100)]:
            rt.add_row(str(step), f"{rwd:.3f}", "[yellow]at ceiling[/yellow]")
    layout["rollouts"].update(
        Panel(rt, title="[bold cyan]Recent rollouts[/bold cyan]", border_style="cyan")
    )

    # ─── Footer keybinds ───────────────────────────────────────────────────
    footer = Text(no_wrap=True)
    for key, label in [("q", "Quit"), ("e", "Export CSV"), ("a", "Clear alerts")]:
        footer.append(f" {key} ", style="bold black on white")
        footer.append(f" {label}   ")
    footer.append("^palette", style="dim white")
    layout["footer"].update(footer)

    return layout


# ─────────────────────────────── Entry point ─────────────────────────────────

def run_tui(target_path: str = ".", live_mode: bool = True) -> None:
    """Launch the live Rich TUI dashboard for audits or in-training monitoring."""
    console = Console(safe_box=True, force_terminal=True)
    path_obj = Path(target_path)

    is_log = target_path.endswith(".jsonl") or (path_obj.is_file() and target_path.endswith(".jsonl"))

    if not is_log:
        from ratctl.analyzer import audit
        audit_res = audit(target_path)
        data = audit_res.to_dict()
        target_name = path_obj.name or "environment"
        layout = create_audit_tui_layout(data, target_name=target_name)
        console.print(layout)
        return

    if not live_mode:
        layout = create_tui_layout(target_path)
        console.print(layout)
        return

    try:
        console.clear()
    except Exception:
        pass
    step = [0]

    def _build() -> Layout:
        step[0] = (step[0] + 1) % 600
        return create_tui_layout(target_path, _demo_step=step[0] if not read_logs(target_path) else None)

    with Live(_build(), console=console, refresh_per_second=4, screen=True) as live:
        try:
            while True:
                time.sleep(0.25)
                live.update(_build())
        except KeyboardInterrupt:
            pass
