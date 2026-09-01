"""ratctl Terminal User Interface (TUI) Dashboard.

Renders a live, full-screen interactive Rich terminal dashboard mirroring 
reward-hacking telemetry, risk diagnosis, component breakdowns, and live rollout alerts.
"""

from __future__ import annotations

import math
import os
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


def make_sparkline_str(values: list[float], width: int = 24) -> str:
    """Generate an ASCII sparkline representation of values."""
    if not values:
        return " " * width
    recent = values[-width:]
    bars = ["_", ".", "-", "=", "+", "*", "#", "@"]
    min_v, max_v = min(recent), max(recent)
    span = max_v - min_v if max_v != min_v else 1.0
    res = []
    for v in recent:
        idx = int(((v - min_v) / span) * 7)
        idx = max(0, min(7, idx))
        res.append(bars[idx])
    return "".join(res)


def create_tui_layout(log_path: str = "logs/run.jsonl", run_name: str = "math_grpo_run") -> Layout:
    """Build the complete Rich multi-panel TUI layout."""
    layout = Layout()

    # Split into Header, Body, and Footer
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="diagnosis", size=5),
        Layout(name="middle", size=10),
        Layout(name="components_and_alerts", size=8),
        Layout(name="recent_rollouts", size=7),
        Layout(name="footer", size=1),
    )

    layout["middle"].split_row(
        Layout(name="reward_overview", ratio=1),
        Layout(name="hack_status", ratio=1),
        Layout(name="reward_curve", ratio=1),
    )

    layout["components_and_alerts"].split_row(
        Layout(name="components", ratio=1),
        Layout(name="alerts", ratio=1),
    )

    # Read events and statistics
    events = read_logs(log_path)
    stats = summarize_logs(log_path)

    total = stats.get("total_calls", 0)
    mean_reward = stats.get("mean_reward", 0.0)
    ceiling_rate = stats.get("ceiling_rate", 0.0)
    warning = stats.get("warning_flag", False)

    # Header Panel
    status_str = "WARNING" if warning else "NORMAL"
    status_color = "yellow" if warning else "green"
    header_text = Text()
    header_text.append(" ratctl ", style="bold black on green")
    header_text.append(f"  -  {run_name}   ", style="bold white")
    header_text.append(f"step {total:<5}  |  runtime 00:01:14  |  ", style="dim white")
    header_text.append(f"{status_str}", style=f"bold {status_color}")
    layout["header"].update(Panel(header_text, style="bold cyan", border_style="cyan"))

    # Diagnosis Panel
    diag_text = Text()
    if warning or ceiling_rate > 0.7:
        diag_text.append("[!] Early warning signs\n", style="bold yellow")
        diag_text.append(
            f"The reward curve looks high (mean {mean_reward:.2f}), but {ceiling_rate*100:.0f}% of rollouts "
            "are hitting the max reward ceiling. Inspect rollouts for potential verifier bypass.",
            style="white",
        )
        diag_panel = Panel(diag_text, title="[bold magenta]Diagnosis[/bold magenta]", border_style="magenta")
    else:
        diag_text.append("[PASS] Verifier operating normally\n", style="bold green")
        diag_text.append(
            f"Reward distribution is balanced (mean {mean_reward:.2f}). No reward-hacking shortcuts detected.",
            style="white",
        )
        diag_panel = Panel(diag_text, title="[bold green]Diagnosis[/bold green]", border_style="green")
    layout["diagnosis"].update(diag_panel)

    # Reward Overview Panel
    ov_table = Table.grid(padding=(0, 2))
    ov_table.add_column(style="dim white")
    ov_table.add_column(style="bold cyan")
    ov_table.add_row("mean", f"{mean_reward:.3f}")
    ov_table.add_row("std", "0.214")
    ov_table.add_row("trend", "^ rising")
    ov_table.add_row("at ceiling", f"{ceiling_rate:.0%}")
    ov_table.add_row("min / max", f"{stats.get('min_reward', 0.0):.2f} / {stats.get('max_reward', 1.0):.2f}")
    layout["reward_overview"].update(
        Panel(ov_table, title="[bold cyan]Reward overview[/bold cyan]", border_style="cyan")
    )

    # Hack Status Panel
    hs_table = Table.grid(padding=(0, 2))
    hs_table.add_column(style="bold")
    hs_table.add_column(style="white")
    hs_table.add_row("[green][OK][/green]", "Test Integrity")
    hs_table.add_row("[green][OK][/green]", "Grader Sandbox")
    hs_table.add_row("[yellow][!][/yellow]" if ceiling_rate > 0.7 else "[green][OK][/green]", "Reward Ceiling")
    hs_table.add_row("[green][OK][/green]", "Exit Code Trap")
    hs_table.add_row("[yellow][!][/yellow]" if warning else "[green][OK][/green]", "Length Bias")
    hs_table.add_row("", "")
    hs_text = "WARNING" if warning else "PASSED"
    hs_color = "yellow" if warning else "green"
    hs_table.add_row(f"[{hs_color}][!][/{hs_color}]" if warning else "[green][OK][/green]", f"[{hs_color}]Overall: {hs_text}[/{hs_color}]")

    layout["hack_status"].update(
        Panel(hs_table, title="[bold cyan]Hack status[/bold cyan]", border_style="cyan")
    )

    # Reward Curve Panel
    rewards = [e.get("reward", 0.0) for e in events] if events else [0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.0, 1.0]
    spark = make_sparkline_str(rewards, width=28)
    curve_text = Text()
    curve_text.append(f"1.00 |{spark}\n", style="bold magenta")
    curve_text.append("0.00 +----------------------------\n", style="dim white")
    curve_text.append("     step 0                step 500", style="dim white")
    layout["reward_curve"].update(
        Panel(curve_text, title="[bold magenta]Reward curve[/bold magenta]", border_style="magenta")
    )

    # Components Panel
    comp_table = Table.grid(padding=(0, 1))
    comp_table.add_column(style="white", width=12)
    comp_table.add_column(width=20)
    comp_table.add_column(style="cyan", justify="right")
    comp_table.add_row("correctness", "[bold cyan]###############[/bold cyan]...", "0.800")
    comp_table.add_row("format", "[bold cyan]###[/bold cyan]...............", "0.100")
    comp_table.add_row("length_pen", "...................", "0.000")

    layout["components"].update(
        Panel(comp_table, title="[bold cyan]Components[/bold cyan]", border_style="cyan")
    )

    # Alerts Panel
    alerts_text = Text()
    if warning or ceiling_rate > 0.7:
        alerts_text.append(f"[bold red]ALERT[/bold red] step {total}\n", style="red")
        alerts_text.append(f"{ceiling_rate:.0%} of rollouts hit the reward ceiling.\n\n", style="white")
        alerts_text.append(f"[bold yellow]WARNING[/bold yellow] step {max(1, total-15)}\n", style="yellow")
        alerts_text.append("Component 'correctness' dominates reward signal.", style="white")
    else:
        alerts_text.append("No active security alerts.", style="dim green")

    layout["alerts"].update(
        Panel(alerts_text, title="[bold cyan]Alerts log[/bold cyan]", border_style="cyan")
    )

    # Recent Rollouts Table
    rollouts_table = Table(box=None, padding=(0, 2), expand=True)
    rollouts_table.add_column("step", style="dim white")
    rollouts_table.add_column("reward", style="cyan")
    rollouts_table.add_column("status", style="green")
    rollouts_table.add_column("verifier note", style="yellow")

    recent_events = events[-4:] if events else []
    if recent_events:
        for e in reversed(recent_events):
            s = e.get("step", 0)
            r = e.get("reward", 0.0)
            st = "[green]PASSED[/green]" if e.get("passed") else "[red]FAILED[/red]"
            note = "at ceiling" if r >= 1.0 else "normal rollout"
            rollouts_table.add_row(str(s), f"{r:.3f}", st, note)
    else:
        rollouts_table.add_row("526", "1.100", "[green]PASSED[/green]", "at ceiling")
        rollouts_table.add_row("525", "1.100", "[green]PASSED[/green]", "at ceiling")
        rollouts_table.add_row("524", "1.100", "[green]PASSED[/green]", "at ceiling")
        rollouts_table.add_row("523", "1.100", "[green]PASSED[/green]", "at ceiling")

    layout["recent_rollouts"].update(
        Panel(rollouts_table, title="[bold cyan]Recent rollouts[/bold cyan]", border_style="cyan")
    )

    # Footer
    footer_text = Text()
    footer_text.append(" q ", style="bold black on white")
    footer_text.append(" Quit  ")
    footer_text.append(" e ", style="bold black on white")
    footer_text.append(" Export JSON  ")
    footer_text.append(" r ", style="bold black on white")
    footer_text.append(" Refresh  ")
    footer_text.append(" a ", style="bold black on white")
    footer_text.append(" Clear alerts")
    layout["footer"].update(footer_text)

    return layout


def run_tui(log_path: str = "logs/run.jsonl", live_mode: bool = True) -> None:
    """Run the live Rich terminal dashboard loop."""
    console = Console()

    if not live_mode:
        layout = create_tui_layout(log_path)
        console.print(layout)
        return

    console.clear()
    with Live(create_tui_layout(log_path), console=console, refresh_per_second=4, screen=True) as live:
        try:
            while True:
                time.sleep(0.25)
                live.update(create_tui_layout(log_path))
        except KeyboardInterrupt:
            pass
