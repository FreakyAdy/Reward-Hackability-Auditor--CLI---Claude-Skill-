"""Tests for ratctl.tui terminal dashboard module."""

from ratctl.tui import create_tui_layout


def test_create_tui_layout():
    layout = create_tui_layout()
    assert layout["header"] is not None
    assert layout["diagnosis"] is not None
    assert layout["middle"] is not None
    assert layout["bottom"] is not None          # was components_and_alerts
    assert layout["rollouts"] is not None        # was recent_rollouts
    assert layout["footer"] is not None
