import asyncio
from typing import Any, cast

import aiohttp
import discord
import pytest
from structlog.testing import capture_logs

from bot.adapters.discord.bot import DiscordBot
from bot.infrastructure.platform_supervisor import PlatformAuthenticationError


@pytest.fixture
def bot(mocker):
    mocker.patch('bot.adapters.discord.bot.discord.Client')
    mocker.patch('bot.adapters.discord.bot.app_commands.CommandTree')
    return DiscordBot('123456789', mocker.Mock())


def _make_message(mocker, *, content: str, author=None, guild_id: int | None = None):
    msg = mocker.MagicMock()
    msg.content = content
    msg.author = author or mocker.MagicMock()
    if guild_id is None:
        msg.guild = None
    else:
        msg.guild = mocker.MagicMock(id=guild_id)
    return msg


class TestOnGuildJoin:
    def test_greets_the_servers_it_joins(self, bot):
        registered = [c.args[0] for c in cast('Any', bot._client.event).call_args_list]

        assert bot._welcome.on_guild_join in registered


class TestOnReady:
    @pytest.mark.anyio
    async def test_invokes_sync_with_retries(self, bot, mocker):
        sync_mock = mocker.patch.object(bot, '_sync_with_retries', mocker.AsyncMock())

        on_ready = bot._make_on_ready()
        await on_ready()

        sync_mock.assert_called_once_with(bot._client, bot._tree)


class TestOnMessage:
    @pytest.mark.anyio
    async def test_skips_self_messages(self, bot, mocker):
        client = bot._client
        msg = _make_message(mocker, content='hi', author=client.user)
        router = mocker.patch.object(bot._router, 'handle_dm', mocker.AsyncMock())

        await bot._make_on_message(client, bot._guild)(msg)

        router.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_empty_content(self, bot, mocker):
        msg = _make_message(mocker, content='')
        router = mocker.patch.object(bot._router, 'handle_dm', mocker.AsyncMock())

        await bot._make_on_message(bot._client, bot._guild)(msg)

        router.assert_not_called()

    @pytest.mark.anyio
    async def test_dm_routed_to_handle_dm(self, bot, mocker):
        msg = _make_message(mocker, content='hello', guild_id=None)
        router = mocker.patch.object(bot._router, 'handle_dm', mocker.AsyncMock())

        await bot._make_on_message(bot._client, bot._guild)(msg)

        router.assert_called_once_with(msg)

    @pytest.mark.anyio
    async def test_skips_other_guild(self, bot, mocker):
        msg = _make_message(mocker, content='hi', guild_id=999)
        bot._guild.id = 123456789
        mention = mocker.patch.object(bot._router, 'handle_mention', mocker.AsyncMock())

        await bot._make_on_message(bot._client, bot._guild)(msg)

        mention.assert_not_called()

    @pytest.mark.anyio
    async def test_skips_when_not_mentioned(self, bot, mocker):
        bot._guild.id = 123456789
        msg = _make_message(mocker, content='no mention', guild_id=123456789)
        mocker.patch.object(DiscordBot, '_mentions_bot', staticmethod(lambda c, m: False))
        mention = mocker.patch.object(bot._router, 'handle_mention', mocker.AsyncMock())

        await bot._make_on_message(bot._client, bot._guild)(msg)

        mention.assert_not_called()

    @pytest.mark.anyio
    async def test_mention_routes_to_handle_mention(self, bot, mocker):
        bot._guild.id = 123456789
        msg = _make_message(mocker, content='<@1> hi', guild_id=123456789)
        mocker.patch.object(DiscordBot, '_mentions_bot', staticmethod(lambda c, m: True))
        mention = mocker.patch.object(bot._router, 'handle_mention', mocker.AsyncMock())

        await bot._make_on_message(bot._client, bot._guild)(msg)

        mention.assert_called_once_with(msg)


class TestMentionsBot:
    def test_returns_false_when_no_user(self, mocker):
        client = mocker.MagicMock()
        client.user = None
        msg = mocker.MagicMock(content='hi')

        assert DiscordBot._mentions_bot(client, msg) is False

    def test_detects_mention_by_id(self, mocker):
        client = mocker.MagicMock()
        client.user = mocker.MagicMock(id=42, name='bot')
        msg = mocker.MagicMock(content='hello <@42>')

        assert DiscordBot._mentions_bot(client, msg) is True

    def test_detects_mention_by_name(self, mocker):
        client = mocker.MagicMock()
        client.user = mocker.MagicMock(id=42)
        client.user.name = 'bot'
        msg = mocker.MagicMock(content='hello @bot')

        assert DiscordBot._mentions_bot(client, msg) is True

    def test_returns_false_without_mention(self, mocker):
        client = mocker.MagicMock()
        client.user = mocker.MagicMock(id=42, name='bot')
        msg = mocker.MagicMock(content='just chatting')

        assert DiscordBot._mentions_bot(client, msg) is False


class TestSyncWithRetries:
    FIRST_GUILD = discord.Object(id=1)
    SECOND_GUILD = discord.Object(id=2)

    @pytest.fixture
    def client(self, mocker):
        return mocker.MagicMock(guilds=[self.FIRST_GUILD, self.SECOND_GUILD])

    @pytest.mark.anyio
    async def test_logs_synced_on_success(self, bot, client, mocker):
        cmd = mocker.MagicMock()
        cmd.name = 'd20'
        bot._tree.sync = mocker.AsyncMock(return_value=[cmd])

        await bot._sync_with_retries(client, bot._tree)

        assert cast('Any', bot._tree.sync).call_args_list[0] == mocker.call()

    @pytest.mark.anyio
    async def test_clears_the_stale_copies_in_every_guild(self, bot, client, mocker):
        bot._tree.sync = mocker.AsyncMock(return_value=[])

        await bot._sync_with_retries(client, bot._tree)

        assert cast('Any', bot._tree.sync).call_args_list == [
            mocker.call(),
            mocker.call(guild=self.FIRST_GUILD),
            mocker.call(guild=self.SECOND_GUILD),
        ]

    @pytest.mark.anyio
    async def test_a_guild_that_refuses_does_not_stop_the_others(self, bot, client, mocker):
        forbidden = discord.Forbidden(mocker.MagicMock(status=403, reason='Forbidden'), 'no scope')
        bot._tree.sync = mocker.AsyncMock(side_effect=[[], forbidden, []])

        with capture_logs() as logs:
            await bot._sync_with_retries(client, bot._tree)

        assert cast('Any', bot._tree.sync).call_args_list[-1] == mocker.call(
            guild=self.SECOND_GUILD
        )
        assert [log['event'] for log in logs] == [
            'discord_guild_clear_refused',
            'discord_connected',
        ]

    @pytest.mark.anyio
    async def test_retries_on_connector_error_then_succeeds(self, bot, client, mocker):
        bot._tree.sync = mocker.AsyncMock(
            side_effect=[
                aiohttp.ClientConnectorError(mocker.MagicMock(), OSError('boom')),
                [],
                [],
                [],
            ]
        )
        sleep = mocker.patch('bot.adapters.discord.bot.asyncio.sleep', mocker.AsyncMock())

        await bot._sync_with_retries(client, bot._tree)

        assert cast('Any', bot._tree.sync).call_count == 4
        sleep.assert_called_once()

    @pytest.mark.anyio
    async def test_gives_up_after_max_retries(self, bot, client, mocker):
        bot._tree.sync = mocker.AsyncMock(
            side_effect=aiohttp.ClientConnectorError(mocker.MagicMock(), OSError('boom'))
        )
        mocker.patch('bot.adapters.discord.bot.asyncio.sleep', mocker.AsyncMock())

        await bot._sync_with_retries(client, bot._tree)

        assert cast('Any', bot._tree.sync).call_count == DiscordBot.MAX_SYNC_RETRIES


class TestRegisterCommands:
    def test_delegates_to_registrar(self, bot, mocker):
        register_all = mocker.patch.object(bot._registrar, 'register_all')

        bot.register_commands()

        register_all.assert_called_once()


class TestStart:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_logs_in_and_connects_to_the_gateway(self, bot, mocker):
        connected = asyncio.Event()
        bot._client.login = mocker.AsyncMock()
        bot._client.connect = mocker.AsyncMock(side_effect=connected.set)

        await bot.start('token')
        await connected.wait()

        bot._client.login.assert_awaited_once_with('token')

    @pytest.mark.anyio
    async def test_reports_a_rejected_token_as_authentication_error(self, bot, mocker):
        bot._client.login = mocker.AsyncMock(side_effect=discord.LoginFailure('Improper token'))
        bot._client.close = mocker.AsyncMock()

        with pytest.raises(PlatformAuthenticationError):
            await bot.start('revoked')

        bot._client.close.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_reraises_a_network_error_for_a_retry(self, bot, mocker):
        unreachable = aiohttp.ClientConnectionError('discord.com unreachable')
        bot._client.login = mocker.AsyncMock(side_effect=unreachable)
        bot._client.close = mocker.AsyncMock()

        with pytest.raises(aiohttp.ClientConnectionError):
            await bot.start('token')

        bot._client.close.assert_awaited_once_with()

    @pytest.fixture
    def sleep(self, mocker):
        return mocker.patch('bot.adapters.discord.bot.asyncio.sleep', new_callable=mocker.AsyncMock)

    @pytest.mark.anyio
    async def test_reconnects_when_the_first_handshake_fails(self, bot, mocker, sleep):
        connected = asyncio.Event()
        logger = mocker.patch('bot.adapters.discord.bot.logger')
        bot._client.login = mocker.AsyncMock()
        bot._client.connect = _connect_failing(1, connected)

        await bot.start('token')
        await asyncio.wait_for(connected.wait(), timeout=1)

        logger.exception.assert_called_once_with('discord_connection_lost', retry_in=5.0)
        sleep.assert_awaited_once_with(5.0)

    @pytest.mark.anyio
    async def test_backs_off_between_failed_connections(self, bot, mocker, sleep):
        connected = asyncio.Event()
        bot._client.login = mocker.AsyncMock()
        bot._client.connect = _connect_failing(8, connected)

        await bot.start('token')
        await asyncio.wait_for(connected.wait(), timeout=1)

        delays = [awaited.args[0] for awaited in sleep.await_args_list]
        assert delays == [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 300.0, 300.0]


def _connect_failing(times: int, connected: asyncio.Event):
    # discord.py's connect() dies like this when the very first handshake fails.
    errors = iter([AttributeError("'NoneType' object has no attribute 'sequence'")] * times)

    async def connect():
        error = next(errors, None)
        if error is not None:
            raise error
        connected.set()

    return connect


class TestStop:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_closes_the_client(self, bot, mocker):
        bot._client.login = mocker.AsyncMock()
        bot._client.connect = mocker.AsyncMock()
        bot._client.close = mocker.AsyncMock()
        await bot.start('token')

        await bot.stop()

        bot._client.close.assert_awaited_once_with()

    @pytest.mark.anyio
    async def test_closes_the_client_when_never_started(self, bot, mocker):
        bot._client.close = mocker.AsyncMock()

        await bot.stop()

        bot._client.close.assert_awaited_once_with()
