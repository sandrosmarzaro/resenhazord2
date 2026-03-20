import httpx
import pytest

from bot.domain.commands.game import GameCommand, IgdbSource
from bot.domain.models.message import ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory

MOCK_IGDB_TOKEN = {'access_token': 'test-token'}

MOCK_IGDB_GAME = [
    {
        'name': 'The Witcher 3',
        'first_release_date': 1431993600,
        'genres': [{'name': 'RPG'}, {'name': 'Adventure'}],
        'platforms': [{'name': 'PC'}, {'name': 'PS4'}],
        'total_rating': 92.5,
        'cover': {'image_id': 'co1wyy'},
    },
]

MOCK_RAWG_RESPONSE = {
    'results': [
        {
            'name': 'Portal 2',
            'released': '2011-04-18',
            'background_image': 'https://media.rawg.io/portal2.jpg',
            'metacritic': 95,
            'genres': [{'name': 'Puzzle'}],
            'platforms': [{'platform': {'name': 'PC'}}, {'platform': {'name': 'Xbox 360'}}],
        },
    ],
}


@pytest.fixture(autouse=True)
def _reset_igdb_token():
    IgdbSource.reset_token()
    yield
    IgdbSource.reset_token()


@pytest.fixture
def command():
    return GameCommand(
        twitch_client_id='test-client-id',
        twitch_client_secret='test-secret',  # noqa: S106
        rawg_api_key='test-rawg-key',
    )


@pytest.fixture
def igdb_token_route(respx_mock):
    return respx_mock.post('https://id.twitch.tv/oauth2/token').mock(
        return_value=httpx.Response(200, json=MOCK_IGDB_TOKEN),
    )


@pytest.fixture
def igdb_games_route(respx_mock):
    return respx_mock.post('https://api.igdb.com/v4/games')


@pytest.fixture
def rawg_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.rawg.io/api/games')


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',game', True),
            (', game', True),
            (', GAME', True),
            (', game show', True),
            (', game dm', True),
            ('game', False),
            ('hello', False),
            (', game extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestIgdb:
    @pytest.mark.anyio
    async def test_returns_image_from_igdb(self, command, igdb_token_route, igdb_games_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=MOCK_IGDB_GAME))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)

    @pytest.mark.anyio
    async def test_caption_contains_game_info(self, command, igdb_token_route, igdb_games_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=MOCK_IGDB_GAME))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'The Witcher 3' in caption
        assert '2015' in caption
        assert 'RPG' in caption
        assert 'PC' in caption
        assert '92/100' in caption

    @pytest.mark.anyio
    async def test_cover_url_uses_igdb_format(self, command, igdb_token_route, igdb_games_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=MOCK_IGDB_GAME))

        messages = await command.run(data)

        expected = 'https://images.igdb.com/igdb/image/upload/t_cover_big_2x/co1wyy.jpg'
        assert messages[0].content.url == expected

    @pytest.mark.anyio
    async def test_game_without_rating(self, command, igdb_token_route, igdb_games_route):
        game_no_rating = [{**MOCK_IGDB_GAME[0], 'total_rating': None}]
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=game_no_rating))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert '⭐' not in caption

    @pytest.mark.anyio
    async def test_game_without_release_date(self, command, igdb_token_route, igdb_games_route):
        game_no_date = [{**MOCK_IGDB_GAME[0], 'first_release_date': None}]
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=game_no_date))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert '(?)' in caption

    @pytest.mark.anyio
    async def test_caches_token(self, command, igdb_token_route, igdb_games_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(return_value=httpx.Response(200, json=MOCK_IGDB_GAME))

        await command.run(data)
        await command.run(data)

        assert igdb_token_route.call_count == 1


class TestRawgFallback:
    @pytest.mark.anyio
    async def test_falls_back_to_rawg_on_igdb_error(
        self, command, igdb_token_route, igdb_games_route, rawg_route
    ):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(return_value=httpx.Response(200, json=MOCK_RAWG_RESPONSE))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert 'Portal 2' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_rawg_caption_info(self, command, igdb_token_route, igdb_games_route, rawg_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(return_value=httpx.Response(200, json=MOCK_RAWG_RESPONSE))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'Portal 2' in caption
        assert '2011' in caption
        assert 'Puzzle' in caption
        assert '95/100' in caption

    @pytest.mark.anyio
    async def test_rawg_cover_url(self, command, igdb_token_route, igdb_games_route, rawg_route):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(return_value=httpx.Response(200, json=MOCK_RAWG_RESPONSE))

        messages = await command.run(data)

        assert messages[0].content.url == 'https://media.rawg.io/portal2.jpg'

    @pytest.mark.anyio
    async def test_rawg_passes_api_key(
        self, command, igdb_token_route, igdb_games_route, rawg_route
    ):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(return_value=httpx.Response(200, json=MOCK_RAWG_RESPONSE))

        await command.run(data)

        request = rawg_route.calls.last.request
        assert 'key=test-rawg-key' in str(request.url)

    @pytest.mark.anyio
    async def test_rawg_filters_games_without_images(
        self, command, igdb_token_route, igdb_games_route, rawg_route
    ):
        response_no_images = {'results': [{'name': 'No Image Game', 'background_image': None}]}
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(return_value=httpx.Response(200, json=response_no_images))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro ao buscar' in messages[0].content.text


class TestBothSourcesFail:
    @pytest.mark.anyio
    async def test_returns_error_when_all_fail(
        self, command, igdb_token_route, igdb_games_route, rawg_route
    ):
        data = GroupCommandDataFactory.build(text=',game')
        igdb_games_route.mock(side_effect=httpx.ConnectError('timeout'))
        rawg_route.mock(side_effect=httpx.ConnectError('timeout'))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Erro ao buscar jogo' in messages[0].content.text


class TestCaption:
    def test_build_caption_with_rating(self):
        from bot.domain.commands.game import GameInfo

        game = GameInfo(
            name='Zelda',
            year='2023',
            genres='Action, Adventure',
            platforms='Switch',
            rating='97/100',
            cover_url='https://example.com/cover.jpg',
        )
        caption = GameCommand._build_caption(game)

        assert '🎮 *Zelda* (2023)' in caption
        assert '🏷️ Action, Adventure' in caption
        assert '🖥️ Switch' in caption
        assert '⭐ 97/100' in caption

    def test_build_caption_without_rating(self):
        from bot.domain.commands.game import GameInfo

        game = GameInfo(
            name='Zelda',
            year='2023',
            genres='Action',
            platforms='Switch',
            rating=None,
            cover_url='https://example.com/cover.jpg',
        )
        caption = GameCommand._build_caption(game)

        assert '⭐' not in caption
