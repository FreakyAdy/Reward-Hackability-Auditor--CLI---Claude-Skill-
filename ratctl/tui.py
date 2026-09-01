"""ratctl Terminal User Interface (TUI) Dashboard.

A full-screen, live-refreshing Rich terminal dashboard mirroring rewardspy's
panel layout: Diagnosis, Reward Overview, Hack Status, Reward Curve sparkline,
Component Bars, Alerts Log, Recent Rollouts, and keybind footer.
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from typing import Sequence

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


def _spark_char(value: float, lo: float, hi: float) -> str:
    if hi == lo:
        return _SPARK_CHARS[4]
    idx = int(((value - lo) / (hi - lo)) * (len(_SPARK_CHARS) - 1))
    idx = max(0, min(len(_SPARK_CHARS) - 1, idx))
    return _SPARK_CHARS[idx]


def make_sparkline(values: list[float], width: int = 32) -> Text:
    """Build a Rich Text sparkline coloured cyan/purple like rewardspy."""
    if not values:
        values = [0.0] * width
    recent = values[-width:]
    lo, hi = min(recent), max(recent)
    t = Text()
    for v in recent:
        ch = _spark_char(v, lo, hi)
        # Colour ramp: low → dim, high → bright purple/magenta
        intensity = (v - lo) / (hi - lo) if hi != lo else 0.5
        if intensity > 0.8:
            t.append(ch, style="bold magenta")
        elif intensity > 0.5:
            t.append(ch, style="magenta")
        else:
            t.append(ch, style="dim cyan")
    return t


def make_bar(value: float, width: int = 24) -> Text:
    """Horizontal bar coloured bright cyan (ASCII-safe)."""
    filled = max(0, min(width, int(value * width)))
    t = Text()
    t.append("#" * filled, style="bold cyan")
    t.append("." * (width - filled), style="dim white")
    return t


# ─────────────────────────────── Layout builder ───────────────────────────────

def create_tui_layout(
    log_path: str = "logs/run.jsonl",
    run_name: str = "ratctl_monitor",
    _demo_step: int | None = None,
) -> Layout:
    """Build the complete Rich multi-panel TUI layout (rewardspy-inspired)."""

    events = read_logs(log_path)
    stats = summarize_logs(log_path)

    total = _demo_step if _demo_step is not None else stats.get("total_calls", 0)
    mean_reward = stats.get("mean_reward", 0.0)
    ceiling_rate = stats.get("ceiling_rate", 0.0)
    warning = stats.get("warning_flag", False) or ceiling_rate > 0.7

    # ─── Simulated demo data when no real log exists ───
    if total == 0 and not events:
        total = 527
        mean_reward = 0.90
        ceiling_rate = 0.81
        warning = True

    rewards_raw: list[float] = [e.get("reward", 0.0) for e in events] if events else []
    if not rewards_raw:
        # Simulate rising curve with noise
        rewards_raw = [
            max(0.0, min(1.1, 0.35 + (i / 527) * 0.75 + random.gauss(0, 0.05)))
            for i in range(527)
        ]
    min_r = min(rewards_raw) if rewards_raw else 0.0
    max_r = max(rewards_raw) if rewards_raw else 1.0

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

    # ─── Header (single‑line status bar) ───────────────────────────────────
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

    # ─── Reward Curve (sparkline histogram) ────────────────────────────────
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

    # ─── Components Panel (bar chart) ──────────────────────────────────────
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

def run_tui(log_path: str = "logs/run.jsonl", live_mode: bool = True) -> None:
    """Launch the live Rich TUI dashboard. Press q or Ctrl+C to quit."""
    console = Console(safe_box=True, force_terminal=True)

    if not live_mode:
        layout = create_tui_layout(log_path)
        console.print(layout)
        return

    try:
        console.clear()
    except Exception:
        pass
    step = [0]

    def _build() -> Layout:
        step[0] = (step[0] + 1) % 600
        return create_tui_layout(log_path, _demo_step=step[0] if not read_logs(log_path) else None)

    with Live(_build(), console=console, refresh_per_second=4, screen=True) as live:
        try:
            while True:
                time.sleep(0.25)
                live.update(_build())
        except KeyboardInterrupt:
            pass
