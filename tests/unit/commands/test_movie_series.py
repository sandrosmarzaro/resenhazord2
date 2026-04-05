import httpx
import pytest

from bot.domain.commands.movie_series import MovieSeriesCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory

OMDB_ALL_RATINGS = {
    'Response': 'True',
    'Ratings': [
        {'Source': 'Internet Movie Database', 'Value': '8.3/10'},
        {'Source': 'Rotten Tomatoes', 'Value': '88%'},
        {'Source': 'Metacritic', 'Value': '73/100'},
    ],
}


@pytest.fixture
def command():
    return MovieSeriesCommand(tmdb_api_key='test-tmdb-key', omdb_api_key='test-omdb-key')


@pytest.fixture
def command_no_omdb():
    return MovieSeriesCommand(tmdb_api_key='test-tmdb-key')


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', filme', True),
            (',filme', True),
            (', FILME', True),
            (', série', True),
            (',serie', True),
            (', filme top100', True),
            (', filme pop', True),
            (', filme pop100', True),
            (', filme pop1000', True),
            (', filme pop top100', True),
            (', filme show', True),
            (', filme tmdb', True),
            ('filme', False),
            ('hello', False),
            (', filme extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @staticmethod
    def _movie_item(**overrides):
        return {
            'id': 603,
            'title': 'The Matrix',
            'poster_path': '/matrix.jpg',
            'genre_ids': [28, 878],
            'vote_average': 8.7,
            'release_date': '1999-03-31',
            'overview': 'A computer hacker learns about the true nature of reality.',
            **overrides,
        }

    @staticmethod
    def _tv_item(**overrides):
        return {
            'id': 1396,
            'name': 'Breaking Bad',
            'poster_path': '/bb.jpg',
            'genre_ids': [18],
            'vote_average': 9.5,
            'first_air_date': '2008-01-20',
            'overview': 'A chemistry teacher turned drug lord.',
            **overrides,
        }

    @staticmethod
    def _mock_omdb(respx_mock, tmdb_id: int = 603, media_type: str = 'movie'):
        respx_mock.get(
            url__regex=rf'.*themoviedb\.org/3/{media_type}/{tmdb_id}/external_ids.*'
        ).mock(return_value=httpx.Response(200, json={'imdb_id': 'tt0133093'}))
        respx_mock.get(url__startswith='http://www.omdbapi.com/').mock(
            return_value=httpx.Response(200, json=OMDB_ALL_RATINGS)
        )

    @pytest.mark.anyio
    async def test_movie_returns_image(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/movie/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(
                200, json={'genres': [{'id': 28, 'name': 'Ação'}, {'id': 878, 'name': 'Ficção'}]}
            )
        )
        self._mock_omdb(respx_mock)

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert '/matrix.jpg' in messages[0].content.url
        caption = messages[0].content.caption
        assert caption is not None
        assert 'The Matrix' in caption
        assert 'Ação' in caption
        assert '1999' in caption

    @pytest.mark.anyio
    async def test_tv_returns_image(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', série')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/tv/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._tv_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': [{'id': 18, 'name': 'Drama'}]})
        )
        self._mock_omdb(respx_mock, tmdb_id=1396, media_type='tv')

        messages = await command.run(data)

        assert len(messages) == 1
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Breaking Bad' in caption
        assert 'Drama' in caption

    @pytest.mark.anyio
    async def test_top_mode_uses_top_rated(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme top100')
        route = respx_mock.get(url__regex=r'.*top_rated.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': [{'id': 28, 'name': 'Ação'}]})
        )
        self._mock_omdb(respx_mock)

        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_pop_with_n_limits_page_range(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', filme pop100')
        route = respx_mock.get(url__regex=r'.*popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': [{'id': 28, 'name': 'Ação'}]})
        )
        self._mock_omdb(respx_mock)
        mock_randint = mocker.patch(
            'bot.domain.commands.movie_series.random.randint', return_value=1
        )

        await command.run(data)

        assert route.called
        mock_randint.assert_called_once_with(1, 5)

    @pytest.mark.anyio
    async def test_default_mode_is_popular(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme')
        route = respx_mock.get(url__regex=r'.*popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': [{'id': 28, 'name': 'Ação'}]})
        )
        self._mock_omdb(respx_mock)

        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_omdb_ratings_appear_in_caption(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/movie/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': []})
        )
        self._mock_omdb(respx_mock)

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '8.3/10' in caption
        assert '88%' in caption
        assert '73/100' in caption

    @pytest.mark.anyio
    async def test_tmdb_flag_skips_omdb(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme tmdb')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/movie/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': []})
        )
        omdb_route = respx_mock.get(url__startswith='http://www.omdbapi.com/').mock(
            return_value=httpx.Response(200, json=OMDB_ALL_RATINGS)
        )

        messages = await command.run(data)

        assert not omdb_route.called
        caption = messages[0].content.caption
        assert '8.7' in caption

    @pytest.mark.anyio
    async def test_omdb_failure_falls_back_to_tmdb_rating(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/movie/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': []})
        )
        respx_mock.get(url__regex=r'.*external_ids.*').mock(
            return_value=httpx.Response(500)
        )

        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '8.7' in caption

    @pytest.mark.anyio
    async def test_no_omdb_key_uses_tmdb_rating(self, command_no_omdb, respx_mock):
        data = GroupCommandDataFactory.build(text=', filme')
        respx_mock.get(url__regex=r'.*themoviedb\.org/3/movie/popular.*').mock(
            return_value=httpx.Response(200, json={'results': [self._movie_item()]})
        )
        respx_mock.get(url__startswith='https://api.themoviedb.org/3/genre/').mock(
            return_value=httpx.Response(200, json={'genres': []})
        )

        messages = await command_no_omdb.run(data)

        caption = messages[0].content.caption
        assert '8.7' in caption
