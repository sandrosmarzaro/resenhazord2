import asyncio

import pytest

from bot.infrastructure.platform_supervisor import PlatformStatus, PlatformSupervisor


class TransientError(Exception):
    pass


class PermanentError(Exception):
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

        await supervisor.start('telegram', connect)

        assert supervisor.statuses() == {'telegram': PlatformStatus.UP}

    @pytest.mark.anyio
    async def test_retries_transient_errors_until_connected(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        connect = mocker.AsyncMock(
            side_effect=[TransientError(), TransientError(), mocker.AsyncMock()]
        )

        await supervisor.start('whatsapp', connect)

        assert connect.await_count == 3
        assert supervisor.statuses() == {'whatsapp': PlatformStatus.UP}

    @pytest.mark.anyio
    async def test_reports_retrying_between_attempts(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        seen: list[PlatformStatus] = []

        async def connect():
            seen.append(supervisor.statuses()['discord'])
            if len(seen) == 1:
                raise TransientError
            return mocker.AsyncMock()

        await supervisor.start('discord', connect)

        assert seen == [PlatformStatus.STARTING, PlatformStatus.RETRYING]

    @pytest.mark.anyio
    async def test_doubles_backoff_up_to_the_cap(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        failures = [TransientError() for _ in range(8)]
        connect = mocker.AsyncMock(side_effect=[*failures, mocker.AsyncMock()])

        await supervisor.start('whatsapp', connect)

        delays = [call.args[0] for call in instant_backoff.await_args_list]
        assert delays == [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 300.0, 300.0]


class TestPermanentFailure:
    @pytest.mark.anyio
    async def test_gives_up_without_retrying(self, mocker, instant_backoff):
        supervisor = PlatformSupervisor()
        connect = mocker.AsyncMock(side_effect=PermanentError('invalid token'))

        await supervisor.start('telegram', connect, (PermanentError,))

        connect.assert_awaited_once_with()
        assert supervisor.statuses() == {'telegram': PlatformStatus.FAILED}

    @pytest.mark.anyio
    async def test_leaves_other_platforms_running(self, mocker):
        supervisor = PlatformSupervisor()
        broken = mocker.AsyncMock(side_effect=PermanentError('invalid token'))
        healthy = mocker.AsyncMock(return_value=mocker.AsyncMock())

        await supervisor.start('telegram', broken, (PermanentError,))
        await supervisor.start('whatsapp', healthy)

        assert supervisor.statuses() == {
            'telegram': PlatformStatus.FAILED,
            'whatsapp': PlatformStatus.UP,
        }


class TestStop:
    @pytest.mark.anyio
    async def test_shuts_down_connected_platforms(self, mocker):
        supervisor = PlatformSupervisor()
        shutdown = mocker.AsyncMock()
        await supervisor.start('telegram', mocker.AsyncMock(return_value=shutdown))

        await supervisor.stop()

        shutdown.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_cancels_platforms_still_retrying(self):
        supervisor = PlatformSupervisor()
        attempted = asyncio.Event()

        async def connect():
            attempted.set()
            raise TransientError

        task = supervisor.start('whatsapp', connect)
        await attempted.wait()

        await supervisor.stop()

        assert task.cancelled()
