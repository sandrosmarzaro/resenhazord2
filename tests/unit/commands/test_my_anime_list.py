import json

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
        'title': {'romaji': 'Naruto'},
        'coverImage': {'extraLarge': 'https://example.com/naruto.jpg'},
        'genres': ['Action', 'Adventure'],
        'tags': [
            {'name': 'Ninja', 'category': 'Theme-Action'},
            {'name': 'Shounen', 'category': 'Demographic'},
            {'name': 'Male Protagonist', 'category': 'Cast-Main Cast'},
        ],
        'studios': {'nodes': [{'name': 'Studio Pierrot'}]},
        'staff': {'edges': []},
        'startDate': {'year': 2002},
        'episodes': 220,
        'chapters': None,
        'averageScore': 80,
        'rankings': [
            {'rank': 30, 'type': 'POPULAR', 'allTime': True},
            {'rank': 500, 'type': 'RATED', 'allTime': True},
        ],
        **overrides,
    }


def _manga_item(**overrides):
    return {
        'title': {'romaji': 'One Piece'},
        'coverImage': {'extraLarge': 'https://example.com/onepiece.jpg'},
        'genres': ['Adventure'],
        'tags': [{'name': 'Pirates', 'category': 'Theme-Other'}],
        'studios': {'nodes': []},
        'staff': {
            'edges': [
                {'role': 'Story & Art', 'node': {'name': {'full': 'Eiichiro Oda'}}},
                {'role': 'Translator (English)', 'node': {'name': {'full': 'Stephen Paul'}}},
            ]
        },
        'startDate': {'year': 1997},
        'episodes': None,
        'chapters': 1100,
        'averageScore': 92,
        'rankings': [{'rank': 1, 'type': 'RATED', 'allTime': True}],
        **overrides,
    }


def _page(*items):
    return httpx.Response(200, json={'data': {'Page': {'media': list(items)}}})


@pytest.fixture
def anilist_route(respx_mock):
    return respx_mock.post('https://graphql.anilist.co')


def _variables(route):
    return json.loads(route.calls.last.request.content)['variables']


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
            (', anime top100', True),
            (', anime top50', True),
            (', manga top250', True),
            (', anime pop', True),
            (', anime pop100', True),
            (', manga pop', True),
            ('anime', False),
            ('hello', False),
            (', anime extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_anime_returns_image_with_info(self, command, anilist_route):
        data = GroupCommandDataFactory.build(text=', anime')
        anilist_route.mock(return_value=_page(_anime_item()))

        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/naruto.jpg'
        assert messages[0].content.caption == (
            '*Naruto*\n\n'
            '🎥 220x \t📅 2002\n'
            '⭐️ 8.0 \t🏆 #500\n'
            '🧬 Action, Adventure\n'
            '📜 Ninja\n'
            '📈 Shounen\n'
            '🎙️ Studio Pierrot'
        )

    @pytest.mark.anyio
    async def test_manga_lists_only_story_and_art_staff(self, command, anilist_route):
        data = GroupCommandDataFactory.build(text=', manga')
        anilist_route.mock(return_value=_page(_manga_item()))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '🖋 Eiichiro Oda' in caption
        assert 'Stephen Paul' not in caption

    @pytest.mark.anyio
    async def test_anime_credits_only_the_studio(self, command, anilist_route):
        data = GroupCommandDataFactory.build(text=', anime')
        staff = {'edges': [{'role': 'Art Director', 'node': {'name': {'full': 'Someone'}}}]}
        anilist_route.mock(return_value=_page(_anime_item(staff=staff)))

        messages = await command.run(data)

        assert messages[0].content.caption.endswith('🎙️ Studio Pierrot')

    @pytest.mark.anyio
    async def test_missing_fields_fall_back(self, command, anilist_route):
        data = GroupCommandDataFactory.build(text=', anime')
        item = _anime_item(
            episodes=None,
            startDate={'year': None},
            averageScore=None,
            rankings=[],
            genres=[],
            tags=[],
            studios={'nodes': []},
        )
        anilist_route.mock(return_value=_page(item))

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '🎥 ? \t📅 ?' in caption
        assert '⭐️ ? \t🏆 #?' in caption
        assert '🧬 Desconhecido' in caption

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('text', 'media_type', 'sort'),
        [
            (', anime', 'ANIME', 'SCORE_DESC'),
            (', manga', 'MANGA', 'SCORE_DESC'),
            (', anime pop', 'ANIME', 'POPULARITY_DESC'),
            (', manga pop', 'MANGA', 'POPULARITY_DESC'),
        ],
    )
    async def test_queries_media_type_and_sort(
        self, command, anilist_route, text, media_type, sort
    ):
        data = GroupCommandDataFactory.build(text=text)
        anilist_route.mock(return_value=_page(_manga_item(), _anime_item()))

        await command.run(data)

        variables = _variables(anilist_route)
        assert variables['type'] == media_type
        assert variables['sort'] == [sort]

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('text', 'max_page'),
        [
            (', anime', 20),
            (', anime top100', 4),
            (', anime pop', 20),
            (', anime pop100', 4),
        ],
    )
    async def test_page_range(self, command, anilist_route, mocker, text, max_page):
        data = GroupCommandDataFactory.build(text=text)
        anilist_route.mock(return_value=_page(_anime_item()))
        mock_randint = mocker.patch(
            'bot.domain.commands.my_anime_list.random.randint', return_value=1
        )

        await command.run(data)

        mock_randint.assert_called_once_with(1, max_page)
        assert _variables(anilist_route)['page'] == 1

    @pytest.mark.anyio
    async def test_top1_picks_only_the_first(self, command, anilist_route):
        data = GroupCommandDataFactory.build(text=', anime top1')
        first = _anime_item(title={'romaji': 'Frieren'})
        anilist_route.mock(return_value=_page(first, _anime_item(), _anime_item()))

        messages = await command.run(data)

        assert messages[0].content.caption.startswith('*Frieren*')
