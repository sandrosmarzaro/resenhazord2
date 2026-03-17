"""Global pytest fixtures."""

import pytest

from bot.application.command_registry import CommandRegistry
from bot.infrastructure.http_client import HttpClient


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons between tests."""
    CommandRegistry.reset()
    HttpClient.reset()
    yield
    CommandRegistry.reset()
    HttpClient.reset()
