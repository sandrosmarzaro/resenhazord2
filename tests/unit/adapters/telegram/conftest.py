import pytest


@pytest.fixture
def port(mocker):
    mock_port = mocker.AsyncMock()
    mock_port.send = mocker.AsyncMock()
    mock_port.send_typing = mocker.AsyncMock()
    return mock_port
