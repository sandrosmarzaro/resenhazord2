from unittest.mock import patch

import pytest

from bot.domain.commands.fuck import FuckCommand
from bot.domain.models.message import RawContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return FuckCommand()


def _mock_response(url='https://example.com/video.mp4'):
    return make_json_response({'image': {'url': url}})


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', fuck @123', True),
            (',fuck @456', True),
            (', FUCK @789', True),
            ('  , fuck @111  ', True),
            (', fuck', False),
            ('fuck @123', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_raw_video_with_mentions(self, command):
        sender = '5511999990001@s.whatsapp.net'
        mentioned = '5511888880001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        with patch('bot.domain.commands.fuck.HttpClient.get', return_value=_mock_response()):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, RawContent)
        content = messages[0].content.content
        assert content['viewOnce'] is True
        assert content['video']['url'] == 'https://example.com/video.mp4'
        assert sender in content['mentions']
        assert mentioned in content['mentions']
        assert 'fudendo' in content['caption']

    @pytest.mark.anyio
    async def test_strips_lid_suffix_from_phones(self, command):
        sender = '5511999990001@lid'
        mentioned = '5511888880001@lid'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        with patch('bot.domain.commands.fuck.HttpClient.get', return_value=_mock_response()):
            messages = await command.run(data)

        content = messages[0].content.content
        assert '@5511999990001' in content['caption']
        assert '@5511888880001' in content['caption']

    @pytest.mark.anyio
    async def test_group_only_rejects_private(self, command):
        data = PrivateCommandDataFactory.build(text=', fuck @123')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'grupo' in messages[0].content.text.lower()

    @pytest.mark.anyio
    async def test_uses_sender_jid_when_no_participant(self, command):
        sender = '5511999990001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @123',
            sender_jid=sender,
            participant=None,
            mentioned_jids=['123@s.whatsapp.net'],
        )

        with patch('bot.domain.commands.fuck.HttpClient.get', return_value=_mock_response()):
            messages = await command.run(data)

        content = messages[0].content.content
        assert sender in content['mentions']
