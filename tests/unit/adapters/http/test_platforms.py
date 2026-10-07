from http import HTTPStatus

import httpx
import pytest

from bot.adapters.http.app import app
from bot.domain.commands.base import Platform
from bot.infrastructure.platform_supervisor import PlatformStatus, PlatformSupervisor


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def supervisor(mocker):
    supervisor = mocker.Mock(spec=PlatformSupervisor)
    app.state.platforms = supervisor
    yield supervisor
    del app.state.platforms


async def _get_platforms() -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://core') as client:
        return await client.get('/v1/ops/platforms')


class TestListPlatforms:
    @pytest.mark.anyio
    async def test_lists_each_configured_platform_with_its_status(self, supervisor):
        supervisor.statuses.return_value = {
            Platform.WHATSAPP: PlatformStatus.UP,
            Platform.TELEGRAM: PlatformStatus.FAILED,
        }

        response = await _get_platforms()

        assert response.status_code == HTTPStatus.OK
        assert response.json() == [
            {'name': 'whatsapp', 'status': 'up'},
            {'name': 'telegram', 'status': 'failed'},
        ]

    @pytest.mark.anyio
    async def test_is_empty_when_no_platform_is_configured(self, supervisor):
        supervisor.statuses.return_value = {}

        response = await _get_platforms()

        assert response.status_code == HTTPStatus.OK
        assert response.json() == []
