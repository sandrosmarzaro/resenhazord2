"""Shared mock HTTP response builders for command tests."""

from unittest.mock import MagicMock


def make_json_response(json_data: dict | list) -> MagicMock:
    """Create a mock HTTP response that returns JSON data."""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status.return_value = None
    return mock


def make_html_response(html: str) -> MagicMock:
    """Create a mock HTTP response that returns HTML text."""
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status.return_value = None
    return mock
