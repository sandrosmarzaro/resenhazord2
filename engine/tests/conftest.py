"""Global pytest fixtures."""

from __future__ import annotations

import pytest

from bot.application.command_registry import CommandRegistry


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset singleton between tests."""
    CommandRegistry.reset()
    yield
    CommandRegistry.reset()
