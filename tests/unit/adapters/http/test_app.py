import aiohttp
import pytest

from bot.adapters.http.app import _run_discord_client


class TestRunDiscordClient:
    @pytest.mark.anyio
    async def test_captures_runtimeerror_tcp_transport_closed(self, mocker):
        bot = mocker.MagicMock()
        bot.client.start = mocker.AsyncMock(
            side_effect=RuntimeError(
                'unable to perform operation on '
                '<TCPTransport closed=True reading=False 0x7f112eb00360>; '
                'the handler is closed'
            )
        )
        logger_mock = mocker.patch('bot.adapters.http.app.logger')

        await _run_discord_client(bot, 'fake-token')

        bot.client.start.assert_awaited_once_with('fake-token')
        logger_mock.exception.assert_called_once()
        assert 'discord_connection_closed' in str(logger_mock.exception.call_args)

    @pytest.mark.anyio
    async def test_re_raises_unexpected_runtimeerror(self, mocker):
        bot = mocker.MagicMock()
        bot.client.start = mocker.AsyncMock(side_effect=RuntimeError('something else'))

        with pytest.raises(RuntimeError, match='something else'):
            await _run_discord_client(bot, 'fake-token')

    @pytest.mark.anyio
    async def test_captures_client_connector_dns_error(self, mocker):
        bot = mocker.MagicMock()
        bot.client.start = mocker.AsyncMock(
            side_effect=aiohttp.ClientConnectorDNSError(
                mocker.MagicMock(), OSError(-3, 'Try again')
            )
        )
        logger_mock = mocker.patch('bot.adapters.http.app.logger')

        await _run_discord_client(bot, 'fake-token')

        bot.client.start.assert_awaited_once_with('fake-token')
        logger_mock.exception.assert_called_once()
        assert 'discord_connection_closed' in str(logger_mock.exception.call_args)

    @pytest.mark.anyio
    async def test_captures_timeout_error(self, mocker):
        bot = mocker.MagicMock()
        bot.client.start = mocker.AsyncMock(side_effect=TimeoutError)
        logger_mock = mocker.patch('bot.adapters.http.app.logger')

        await _run_discord_client(bot, 'fake-token')

        bot.client.start.assert_awaited_once_with('fake-token')
        logger_mock.exception.assert_called_once()
        assert 'discord_connection_closed' in str(logger_mock.exception.call_args)
