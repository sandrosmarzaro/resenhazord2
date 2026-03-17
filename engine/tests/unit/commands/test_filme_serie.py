import pytest

from bot.domain.commands.filme_serie import FilmeSerieCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return FilmeSerieCommand(tmdb_api_key='test-api-key')


def _movie_item(**overrides):
    return {
        'title': 'The Matrix',
        'poster_path': '/matrix.jpg',
        'genre_ids': [28, 878],
        'vote_average': 8.7,
        'release_date': '1999-03-31',
        'overview': 'A computer hacker learns about the true nature of reality.',
        **overrides,
    }


def _tv_item(**overrides):
    return {
        'name': 'Breaking Bad',
        'poster_path': '/bb.jpg',
        'genre_ids': [18],
        'vote_average': 9.5,
        'first_air_date': '2008-01-20',
        'overview': 'A chemistry teacher turned drug lord.',
        **overrides,
    }


def _genres_response(genres):
    return make_json_response({'genres': genres})


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', filme', True),
            (',filme', True),
            (', FILME', True),
            (', série', True),
            (',serie', True),
            (', filme top', True),
            (', filme pop', True),
            (', filme show', True),
            ('filme', False),
            ('hello', False),
            (', filme extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_movie_returns_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', filme')
        movie_resp = make_json_response({'results': [_movie_item()]})
        genres_resp = _genres_response([{'id': 28, 'name': 'Ação'}, {'id': 878, 'name': 'Ficção'}])

        mocker.patch(
            'bot.domain.commands.filme_serie.HttpClient.get',
            side_effect=[movie_resp, genres_resp],
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert '/matrix.jpg' in messages[0].content.url
        caption = messages[0].content.caption
        assert 'The Matrix' in caption
        assert 'Ação' in caption
        assert '1999' in caption

    @pytest.mark.anyio
    async def test_tv_returns_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', série')
        tv_resp = make_json_response({'results': [_tv_item()]})
        genres_resp = _genres_response([{'id': 18, 'name': 'Drama'}])

        mocker.patch(
            'bot.domain.commands.filme_serie.HttpClient.get',
            side_effect=[tv_resp, genres_resp],
        )
        messages = await command.run(data)

        assert len(messages) == 1
        caption = messages[0].content.caption
        assert 'Breaking Bad' in caption
        assert 'Drama' in caption

    @pytest.mark.anyio
    async def test_top_mode_uses_top_rated(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', filme top')
        movie_resp = make_json_response({'results': [_movie_item()]})
        genres_resp = _genres_response([{'id': 28, 'name': 'Ação'}])

        mock_get = mocker.patch(
            'bot.domain.commands.filme_serie.HttpClient.get',
            side_effect=[movie_resp, genres_resp],
        )
        await command.run(data)

        url = mock_get.call_args_list[0][0][0]
        assert 'top_rated' in url

    @pytest.mark.anyio
    async def test_default_mode_is_popular(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', filme')
        movie_resp = make_json_response({'results': [_movie_item()]})
        genres_resp = _genres_response([{'id': 28, 'name': 'Ação'}])

        mock_get = mocker.patch(
            'bot.domain.commands.filme_serie.HttpClient.get',
            side_effect=[movie_resp, genres_resp],
        )
        await command.run(data)

        url = mock_get.call_args_list[0][0][0]
        assert 'popular' in url
