import httpx
import pytest

from bot.domain.commands.my_anime_list import MyAnimeListCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return MyAnimeListCommand()


def _anime_item(**overrides):
    return {
        'title': 'Naruto',
        'images': {'webp': {'large_image_url': 'https://example.com/naruto.webp'}},
        'genres': [{'name': 'Action'}, {'name': 'Adventure'}],
        'themes': [{'name': 'Shounen'}],
        'demographics': [{'name': 'Shounen'}],
        'studios': [{'name': 'Studio Pierrot'}],
        'aired': {'prop': {'from': {'year': 2002}}},
        'episodes': 220,
        'score': 8.0,
        'rank': 500,
        **overrides,
    }


def _manga_item(**overrides):
    return {
        'title': 'One Piece',
        'images': {'webp': {'large_image_url': 'https://example.com/onepiece.webp'}},
        'genres': [{'name': 'Adventure'}],
        'themes': [{'name': 'Pirates'}],
        'demographics': [{'name': 'Shounen'}],
        'authors': [{'name': 'Oda, Eiichiro'}],
        'published': {'prop': {'from': {'year': 1997}}},
        'chapters': 1100,
        'score': 9.2,
        'rank': 1,
        **overrides,
    }


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', anime', True),
            (',anime', True),
            (', ANIME', True),
            (', manga', True),
            (',manga', True),
            (', anime show', True),
            (', anime dm', True),
            ('anime', False),
            ('hello', False),
            (', anime extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_anime_returns_image_with_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', anime')
        respx_mock.get(url__regex=r'.*/top/anime.*').mock(
            return_value=httpx.Response(200, json={'data': [_anime_item()]})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Naruto' in caption
        assert 'Action' in caption
        assert 'Studio Pierrot' in caption
        assert '🎥' in caption

    @pytest.mark.anyio
    async def test_manga_returns_image_with_info(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', manga')
        respx_mock.get(url__regex=r'.*/top/manga.*').mock(
            return_value=httpx.Response(200, json={'data': [_manga_item()]})
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        caption = messages[0].content.caption
        assert caption is not None
        assert 'One Piece' in caption
        assert 'Oda, Eiichiro' in caption
        assert '📚' in caption

    @pytest.mark.anyio
    async def test_calls_correct_api_for_anime(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', anime')
        route = respx_mock.get(url__regex=r'.*/top/anime.*').mock(
            return_value=httpx.Response(200, json={'data': [_anime_item()]})
        )
        await command.run(data)

        url = str(route.calls.last.request.url)
        assert '/top/anime' in url

    @pytest.mark.anyio
    async def test_calls_correct_api_for_manga(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', manga')
        route = respx_mock.get(url__regex=r'.*/top/manga.*').mock(
            return_value=httpx.Response(200, json={'data': [_manga_item()]})
        )
        await command.run(data)

        url = str(route.calls.last.request.url)
        assert '/top/manga' in url
