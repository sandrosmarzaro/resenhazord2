import httpx
import pytest

from bot.domain.commands.fuck import FuckCommand
from bot.domain.models.message import TextContent, VideoBufferContent
from bot.domain.services.mp4_remux import Mp4Remux
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


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
    AUTH_URL = 'https://api.redgifs.com/v2/auth/temporary'
    SEARCH_URL = 'https://api.redgifs.com/v2/gifs/search'
    VIDEO_URL = 'https://media.redgifs.com/Clip-mobile.mp4'

    @pytest.fixture
    def search_route(self, respx_mock, mocker):
        respx_mock.get(self.AUTH_URL).mock(return_value=httpx.Response(200, json={'token': 't'}))
        respx_mock.get(self.VIDEO_URL).mock(return_value=httpx.Response(200, content=b'm4v'))
        mocker.patch.object(Mp4Remux, 'remux', return_value=b'isom')
        item = {'type': 1, 'tags': ['Sex'], 'niches': [], 'urls': {'sd': self.VIDEO_URL}}
        return respx_mock.get(url__startswith=self.SEARCH_URL).mock(
            return_value=httpx.Response(200, json={'gifs': [item]})
        )

    @pytest.mark.anyio
    async def test_returns_remuxed_video_with_mentions(self, command, search_route):
        sender = '5511999990001@s.whatsapp.net'
        mentioned = '5511888880001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        messages = await command.run(data)

        assert len(messages) == 1
        content = messages[0].content
        assert isinstance(content, VideoBufferContent)
        assert content.data == b'isom'
        assert content.view_once is True
        assert content.mentions == [sender, mentioned]
        assert 'fudendo' in content.caption

    @pytest.mark.anyio
    async def test_sends_the_mentions_to_the_gateway(self, command, search_route):
        sender = '5511999990001@s.whatsapp.net'
        mentioned = '5511888880001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        messages = await command.run(data)

        assert messages[0].to_dict()['content']['mentions'] == [sender, mentioned]

    @pytest.mark.anyio
    async def test_strips_lid_suffix_from_phones(self, command, search_route):
        sender = '5511999990001@lid'
        mentioned = '5511888880001@lid'
        data = GroupCommandDataFactory.build(
            text=', fuck @5511888880001',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[mentioned],
        )

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '@5511999990001' in caption
        assert '@5511888880001' in caption

    @pytest.mark.anyio
    async def test_group_only_rejects_private(self, command):
        data = PrivateCommandDataFactory.build(text=', fuck @123')

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'grupo' in messages[0].content.text.lower()

    @pytest.mark.anyio
    async def test_uses_sender_jid_when_no_participant(self, command, search_route):
        sender = '5511999990001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @123',
            sender_jid=sender,
            participant=None,
            mentioned_jids=['123@s.whatsapp.net'],
        )

        messages = await command.run(data)

        assert sender in messages[0].content.mentions

    @pytest.mark.anyio
    async def test_empty_mentioned_when_no_jids(self, command, search_route):
        sender = '5511999990001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @123',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=[],
        )

        messages = await command.run(data)

        content = messages[0].content
        assert '@' in content.caption
        assert '' in content.mentions

    @pytest.mark.anyio
    async def test_searches_sex_videos(self, command, search_route):
        sender = '5511999990001@s.whatsapp.net'
        data = GroupCommandDataFactory.build(
            text=', fuck @123',
            sender_jid=sender,
            participant=sender,
            mentioned_jids=['123@s.whatsapp.net'],
        )

        await command.run(data)

        params = search_route.calls.last.request.url.params
        assert (params['tags'], params['type']) == ('Sex', 'g')
