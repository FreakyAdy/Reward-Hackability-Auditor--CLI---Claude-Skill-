"""Tests for ratctl.tui terminal dashboard module."""

from ratctl.tui import create_tui_layout


def test_create_tui_layout():
    layout = create_tui_layout()
    assert layout["header"] is not None
    assert layout["diagnosis"] is not None
    assert layout["middle"] is not None
    assert layout["components_and_alerts"] is not None
    assert layout["recent_rollouts"] is not None
    assert layout["footer"] is not None
