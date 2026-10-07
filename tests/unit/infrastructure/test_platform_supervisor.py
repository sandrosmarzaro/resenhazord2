import asyncio

import pytest

from bot.domain.commands.base import Platform
from bot.infrastructure.platform_supervisor import (
    PlatformAuthenticationError,
    PlatformStatus,
    PlatformSupervisor,
)


class TransientError(Exception):
    pass


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def instant_backoff(mocker):
    return mocker.patch(
        'bot.infrastructure.platform_supervisor.asyncio.sleep', new_callable=mocker.AsyncMock
    )


class TestConnect:
    @pytest.mark.anyio
    async def test_reports_up_once_connected(self, mocker):
        supervisor = PlatformSupervisor()
        connect = mocker.AsyncMock(return_value=mocker.AsyncMock())

        await supervisor.start(Platform.TELEGRAM, connect)

        assert supervisor.statuses() == {Platform.TELEGRAM: PlatformStatus.UP}

    @pytest.mark.anyio
    async def test_retries_transient_errors_until_connected(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        connect = mocker.AsyncMock(
            side_effect=[TransientError(), TransientError(), mocker.AsyncMock()]
        )

        await supervisor.start(Platform.WHATSAPP, connect)

        assert connect.await_count == 3
        assert supervisor.statuses() == {Platform.WHATSAPP: PlatformStatus.UP}

    @pytest.mark.anyio
    async def test_reports_retrying_between_attempts(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        seen: list[PlatformStatus] = []

        async def connect():
            seen.append(supervisor.statuses()[Platform.DISCORD])
            if len(seen) == 1:
                raise TransientError
            return mocker.AsyncMock()

        await supervisor.start(Platform.DISCORD, connect)

        assert seen == [PlatformStatus.STARTING, PlatformStatus.RETRYING]

    @pytest.mark.anyio
    async def test_doubles_backoff_up_to_the_cap(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        failures = [TransientError() for _ in range(8)]
        connect = mocker.AsyncMock(side_effect=[*failures, mocker.AsyncMock()])

        await supervisor.start(Platform.WHATSAPP, connect)

        delays = [call.args[0] for call in instant_backoff.await_args_list]
        assert delays == [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 300.0, 300.0]


class TestPermanentFailure:
    @pytest.mark.anyio
    async def test_gives_up_without_retrying(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        connect = mocker.AsyncMock(side_effect=PlatformAuthenticationError(Platform.TELEGRAM))

        await supervisor.start(Platform.TELEGRAM, connect)

        connect.assert_awaited_once_with()
        assert supervisor.statuses() == {Platform.TELEGRAM: PlatformStatus.FAILED}

    @pytest.mark.anyio
    async def test_leaves_other_platforms_running(self, mocker):
        supervisor = PlatformSupervisor()
        broken = mocker.AsyncMock(side_effect=PlatformAuthenticationError(Platform.TELEGRAM))
        healthy = mocker.AsyncMock(return_value=mocker.AsyncMock())

        await supervisor.start(Platform.TELEGRAM, broken)
        await supervisor.start(Platform.WHATSAPP, healthy)

        assert supervisor.statuses() == {
            Platform.TELEGRAM: PlatformStatus.FAILED,
            Platform.WHATSAPP: PlatformStatus.UP,
        }


class TestStop:
    @pytest.mark.anyio
    async def test_shuts_down_connected_platforms(self, mocker):
        supervisor = PlatformSupervisor()
        shutdown = mocker.AsyncMock()
        await supervisor.start(Platform.TELEGRAM, mocker.AsyncMock(return_value=shutdown))

        await supervisor.stop()

        shutdown.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_cancels_platforms_still_retrying(self):
        supervisor = PlatformSupervisor()
        attempted = asyncio.Event()

        async def connect():
            attempted.set()
            raise TransientError

        task = supervisor.start(Platform.WHATSAPP, connect)
        await attempted.wait()

        await supervisor.stop()

        assert task.cancelled()
