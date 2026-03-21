import httpx
import pytest

from bot.domain.commands.fuck import FuckCommand
from bot.domain.models.message import RawContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

NSFW_URL = 'https://nsfwhub.onrender.com/nsfw?type=fuck'


@pytest.fixture
def command():
    return FuckCommand()


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
    async def test_returns_raw_video_with_mentions(self, command, respx_mock):
        sender = '5511999990001@s.whatsapp.net'
        mentioned = '5511888880001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        respx_mock.get(NSFW_URL).mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/video.mp4'}}
            )
        )
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
    async def test_strips_lid_suffix_from_phones(self, command, respx_mock):
        sender = '5511999990001@lid'
        mentioned = '5511888880001@lid'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        respx_mock.get(NSFW_URL).mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/video.mp4'}}
            )
        )
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
    async def test_uses_sender_jid_when_no_participant(self, command, respx_mock):
        sender = '5511999990001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @123',
            sender_jid=sender,
            participant=None,
            mentioned_jids=['123@s.whatsapp.net'],
        )

        respx_mock.get(NSFW_URL).mock(
            return_value=httpx.Response(
                200, json={'image': {'url': 'https://example.com/video.mp4'}}
            )
        )
        messages = await command.run(data)

        content = messages[0].content.content
        assert sender in content['mentions']
