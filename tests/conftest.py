"""Shared test fixtures and helpers."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def vulnerable_openenv_path():
    """Path to the vulnerable OpenEnv test fixture."""
    return FIXTURES_DIR / "vulnerable_openenv"


@pytest.fixture
def clean_openenv_path():
    """Path to the clean OpenEnv test fixture."""
    return FIXTURES_DIR / "clean_openenv"


@pytest.fixture
def vulnerable_gymnasium_path():
    """Path to the vulnerable Gymnasium test fixture."""
    return FIXTURES_DIR / "vulnerable_gymnasium"


@pytest.fixture
def clean_gymnasium_path():
    """Path to the clean Gymnasium test fixture."""
    return FIXTURES_DIR / "clean_gymnasium"
