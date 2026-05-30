import pytest

from bot.domain.commands.oi import OiCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command():
    return OiCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', oi', True),
            (',oi', True),
            (', OI', True),
            (',OI', True),
            ('  , oi  ', True),
            ('oi', False),
            ('hello', False),
            ('oi,', False),
            (', oi test', False),
            (', oie', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_message_mentioning_sender_in_group(self, command):
        data = GroupCommandDataFactory.build(text=', oi')

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].jid == data.jid
        assert isinstance(messages[0].content, TextContent)
        assert '@' in messages[0].content.text
        assert data.participant in messages[0].content.mentions

    @pytest.mark.anyio
    async def test_uses_sender_jid_in_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=', oi')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert data.sender_jid in messages[0].content.mentions

    @pytest.mark.anyio
    async def test_includes_expiration(self, command):
        data = GroupCommandDataFactory.build(text=', oi', expiration=86400)

        messages = await command.run(data)

        assert messages[0].expiration == 86400

    @pytest.mark.anyio
    async def test_includes_quoted_message_id(self, command):
        data = GroupCommandDataFactory.build(text=', oi', message_id='MSG_42')

        messages = await command.run(data)

        assert messages[0].quoted_message_id == 'MSG_42'

    @pytest.mark.anyio
    async def test_discord_uses_native_mention_format(self, command):
        data = GroupCommandDataFactory.build(
            text=', oi', platform='discord', sender_jid='123456789'
        )

        messages = await command.run(data)

        assert '<@123456789>' in messages[0].content.text
        assert 'Vai se foder' in messages[0].content.text

    @pytest.mark.anyio
    async def test_telegram_uses_push_name(self, command):
        data = GroupCommandDataFactory.build(text=', oi', platform='telegram', push_name='João')

        messages = await command.run(data)

        assert 'João' in messages[0].content.text
        assert 'Vai se foder' in messages[0].content.text

    @pytest.mark.anyio
    async def test_whatsapp_text_contains_sender_phone(self, command):
        data = GroupCommandDataFactory.build(
            text=', oi', participant='5531999887766@s.whatsapp.net'
        )

        messages = await command.run(data)

        assert '5531999887766' in messages[0].content.text
