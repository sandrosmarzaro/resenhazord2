from typing import ClassVar

import httpx
import pytest

from bot.domain.commands.music import MusicCommand
from bot.domain.models.message import AudioContent, ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return MusicCommand(jamendo_client_id='test-client-id')


@pytest.fixture
def deezer_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.deezer.com/chart/')


@pytest.fixture
def jamendo_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.jamendo.com/')


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',musica', True),
            (', música', True),
            (', musica rock', True),
            (', musica free', True),
            (', musica free jazz', True),
            (', MUSICA', True),
            (', musica show', True),
            (', musica dm', True),
            ('musica', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestDeezer:
    MOCK_RESPONSE: ClassVar[dict] = {
        'data': [
            {
                'title': 'Blinding Lights',
                'artist': {'name': 'The Weeknd'},
                'album': {
                    'title': 'After Hours',
                    'cover_medium': 'https://api.deezer.com/album/cover.jpg',
                },
                'duration': 203,
                'preview': 'https://cdns-preview.deezer.com/preview.mp3',
            },
        ],
    }

    @pytest.mark.anyio
    async def test_returns_image_and_audio(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)

        assert len(messages) == 2
        assert isinstance(messages[0].content, ImageContent)
        assert isinstance(messages[1].content, AudioContent)

    @pytest.mark.anyio
    async def test_caption_contains_track_info(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'Blinding Lights' in caption
        assert 'The Weeknd' in caption
        assert 'After Hours' in caption
        assert '3:23' in caption

    @pytest.mark.anyio
    async def test_image_url_is_album_cover(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)

        assert messages[0].content.url == 'https://api.deezer.com/album/cover.jpg'

    @pytest.mark.anyio
    async def test_audio_url_is_preview(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)

        assert messages[1].content.url == 'https://cdns-preview.deezer.com/preview.mp3'

    @pytest.mark.anyio
    async def test_genre_selects_correct_deezer_id(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica rock')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        await command.run(data)

        request = deezer_route.calls.last.request
        assert '/152/' in str(request.url)

    @pytest.mark.anyio
    async def test_unknown_genre_lists_known_genres(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica xyzgenre')

        messages = await command.run(data)

        assert not deezer_route.called
        assert 'sertanejo' in messages[0].content.text

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('text', 'genre_id'),
        [(',musica Forró', 76), (',musica hip hop', 116), (',musica eletrônica', 106)],
    )
    async def test_accented_or_spaced_genre_matches(self, command, deezer_route, text, genre_id):
        data = GroupCommandDataFactory.build(text=text)
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        await command.run(data)

        request = deezer_route.calls.last.request
        assert f'/{genre_id}/' in str(request.url)

    @pytest.mark.anyio
    async def test_caption_shows_genre_tag(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica jazz')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'jazz' in caption

    @pytest.mark.anyio
    async def test_no_genre_shows_all_tag(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'all' in caption

    @pytest.mark.anyio
    async def test_empty_tracks_returns_error(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(return_value=httpx.Response(200, json={'data': []}))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Não encontrei' in messages[0].content.text

    @pytest.mark.anyio
    async def test_api_error_returns_error_message(self, command, deezer_route):
        data = GroupCommandDataFactory.build(text=',musica')
        deezer_route.mock(side_effect=httpx.ConnectError('timeout'))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'não consegui buscar música' in messages[0].content.text


class TestJamendo:
    MOCK_RESPONSE: ClassVar[dict] = {
        'results': [
            {
                'name': 'Sunset Vibes',
                'artist_name': 'Indie Artist',
                'album_name': 'Summer Chill',
                'duration': 240,
                'releasedate': '2024-06-15',
                'image': 'https://usercontent.jamendo.com/image.jpg',
                'audio': 'https://mp3d.jamendo.com/track.mp3',
            },
        ],
    }

    @pytest.mark.anyio
    async def test_free_flag_uses_jamendo(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)

        assert len(messages) == 2
        assert isinstance(messages[0].content, ImageContent)
        assert isinstance(messages[1].content, AudioContent)

    @pytest.mark.anyio
    async def test_caption_contains_jamendo_info(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        messages = await command.run(data)
        caption = messages[0].content.caption

        assert 'Sunset Vibes' in caption
        assert 'Indie Artist' in caption
        assert 'Summer Chill' in caption
        assert '4:00' in caption
        assert '2024-06-15' in caption

    @pytest.mark.anyio
    async def test_free_with_genre(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free rock')
        jamendo_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        await command.run(data)

        request = jamendo_route.calls.last.request
        assert 'tags=rock' in str(request.url)

    @pytest.mark.anyio
    async def test_free_unknown_genre_lists_known_genres(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free unknowngenre')

        messages = await command.run(data)

        assert not jamendo_route.called
        assert 'techno' in messages[0].content.text

    @pytest.mark.anyio
    async def test_free_without_genre_picks_random(self, command, jamendo_route, mocker):
        mocker.patch('bot.domain.commands.music.random.choice', return_value='jazz')
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        await command.run(data)

        request = jamendo_route.calls.last.request
        assert 'tags=jazz' in str(request.url)

    @pytest.mark.anyio
    async def test_passes_client_id(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(return_value=httpx.Response(200, json=self.MOCK_RESPONSE))

        await command.run(data)

        request = jamendo_route.calls.last.request
        assert 'client_id=test-client-id' in str(request.url)

    @pytest.mark.anyio
    async def test_empty_results_returns_error(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(return_value=httpx.Response(200, json={'results': []}))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Não encontrei' in messages[0].content.text

    @pytest.mark.anyio
    async def test_api_error_returns_error_message(self, command, jamendo_route):
        data = GroupCommandDataFactory.build(text=',musica free')
        jamendo_route.mock(side_effect=httpx.ConnectError('timeout'))

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'não consegui buscar música' in messages[0].content.text


class TestDuration:
    @pytest.mark.parametrize(
        ('seconds', 'expected'),
        [
            (0, '0:00'),
            (30, '0:30'),
            (60, '1:00'),
            (90, '1:30'),
            (203, '3:23'),
            (3600, '60:00'),
        ],
    )
    def test_format_duration(self, seconds, expected):
        assert MusicCommand._format_duration(seconds) == expected
