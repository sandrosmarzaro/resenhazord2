import pytest

from bot.adapters.discord.guild_welcome import DiscordGuildWelcome
from bot.data.welcome_messages import DISCORD_WELCOME


def _channel(mocker, *, writable: bool):
    channel = mocker.MagicMock()
    channel.send = mocker.AsyncMock()
    channel.permissions_for.return_value = mocker.MagicMock(send_messages=writable)
    return channel


def _guild(mocker, *, system_channel, text_channels):
    return mocker.MagicMock(id=1, system_channel=system_channel, text_channels=text_channels)


class TestGreetsOnJoin:
    @pytest.mark.anyio
    async def test_posts_in_the_system_channel(self, mocker):
        system = _channel(mocker, writable=True)
        other = _channel(mocker, writable=True)

        await DiscordGuildWelcome().on_guild_join(
            _guild(mocker, system_channel=system, text_channels=[other])
        )

        system.send.assert_awaited_once_with(DISCORD_WELCOME)
        other.send.assert_not_awaited()

    @pytest.mark.anyio
    @pytest.mark.parametrize('system_writable', [None, False], ids=['no-system', 'read-only'])
    async def test_falls_back_to_the_first_writable_text_channel(self, mocker, system_writable):
        system = None if system_writable is None else _channel(mocker, writable=False)
        read_only = _channel(mocker, writable=False)
        writable = _channel(mocker, writable=True)

        await DiscordGuildWelcome().on_guild_join(
            _guild(mocker, system_channel=system, text_channels=[read_only, writable])
        )

        writable.send.assert_awaited_once_with(DISCORD_WELCOME)
        read_only.send.assert_not_awaited()

    @pytest.mark.anyio
    async def test_stays_quiet_without_a_writable_channel(self, mocker):
        read_only = _channel(mocker, writable=False)

        await DiscordGuildWelcome().on_guild_join(
            _guild(mocker, system_channel=None, text_channels=[read_only])
        )

        read_only.send.assert_not_awaited()

    def test_welcome_uses_discord_bold_and_slash_menu(self):
        assert '**E aí, galera!' in DISCORD_WELCOME
        assert '/menu' in DISCORD_WELCOME
