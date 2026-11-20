import pytest

from bot.domain.commands.links import LinksCommand
from tests.factories.command_data import GroupCommandDataFactory

WHATSAPP_JID = '5527999990000@s.whatsapp.net'
DISCORD_APP_ID = '1226632697363959951'
TELEGRAM_USERNAME = 'resenhazord_bot'
WHATSAPP_LINK = '💬 WhatsApp: https://wa.me/5527999990000'
DISCORD_LINK = (
    '🎮 Discord: https://discord.com/oauth2/authorize?client_id=1226632697363959951'
    '&scope=bot+applications.commands&permissions=2147534848'
)
TELEGRAM_LINK = '✈️ Telegram: https://t.me/resenhazord_bot'


async def run_links(whatsapp_jid: str, discord_app_id: str, telegram_username: str) -> str:
    command = LinksCommand(whatsapp_jid, discord_app_id, telegram_username)
    data = GroupCommandDataFactory.build(text=',links')

    messages = await command.run(data)

    return messages[0].content.text


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',links', True),
            (', convite', True),
            (',invite', True),
            (',links discord', False),
            (',link', False),
        ],
    )
    def test_matches(self, text, expected):
        command = LinksCommand(WHATSAPP_JID, DISCORD_APP_ID, TELEGRAM_USERNAME)

        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_lists_a_link_per_platform(self):
        text = await run_links(WHATSAPP_JID, DISCORD_APP_ID, TELEGRAM_USERNAME)

        assert text == (
            f'*Resenhazord em todo lugar* 🤖\n\n{WHATSAPP_LINK}\n{DISCORD_LINK}\n{TELEGRAM_LINK}'
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('settings', 'missing_link'),
        [
            (('', DISCORD_APP_ID, TELEGRAM_USERNAME), WHATSAPP_LINK),
            ((WHATSAPP_JID, '', TELEGRAM_USERNAME), DISCORD_LINK),
            ((WHATSAPP_JID, DISCORD_APP_ID, ''), TELEGRAM_LINK),
        ],
    )
    async def test_skips_a_platform_without_its_setting(self, settings, missing_link):
        text = await run_links(*settings)

        assert missing_link not in text
        assert text.count('https://') == 2
