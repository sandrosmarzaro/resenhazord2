import pytest

from bot.domain.commands.adm import AdmCommand
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

CHAT_JID = '120363044041082732@g.us'
BOT_JID = '5500000000000@s.whatsapp.net'


@pytest.fixture
def command(mock_whatsapp):
    return AdmCommand(whatsapp=mock_whatsapp)


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',adm', True),
            (', adm', True),
            (', ADM', True),
            ('adm', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        data = PrivateCommandDataFactory.build(text=',adm')
        messages = await command.run(data)

        assert len(messages) == 1
        assert 'só funciona em grupo' in messages[0].content.text


class TestExecute:
    @pytest.mark.anyio
    async def test_insults_admins(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': '5511999990000@s.whatsapp.net', 'admin': 'admin'},
                {'id': '5511999990001@s.whatsapp.net', 'admin': 'superadmin'},
                {'id': '5511999990002@s.whatsapp.net', 'admin': None},
            ],
        }
        data = GroupCommandDataFactory.build(text=',adm', jid=CHAT_JID)

        messages = await command.run(data)

        assert len(messages) == 1
        text = messages[0].content.text
        assert 'Vai se foder administração!' in text
        assert '@5511999990000' in text
        assert '@5511999990001' in text
        assert '@5511999990002' not in text
        assert messages[0].content.mentions is not None
        assert len(messages[0].content.mentions) == 2

    @pytest.mark.anyio
    async def test_includes_random_swearing(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': '5511999990000@s.whatsapp.net', 'admin': 'admin'},
            ],
        }
        data = GroupCommandDataFactory.build(text=',adm', jid=CHAT_JID)

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Você é ' in text

    @pytest.mark.anyio
    async def test_strips_jid_suffix(self, command, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = {
            'participants': [
                {'id': '5511999990000@lid', 'admin': 'admin'},
            ],
        }
        data = GroupCommandDataFactory.build(text=',adm', jid=CHAT_JID)

        messages = await command.run(data)

        assert '@5511999990000' in messages[0].content.text
