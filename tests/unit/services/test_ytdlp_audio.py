import pytest

from bot.domain.exceptions import ExternalServiceError
from bot.domain.services.ytdlp_audio import YtDlpAudioService

_REQUESTER = {'requested_by': 'TestUser', 'requested_by_id': 123}
_SUBPROCESS_TARGET = 'asyncio.create_subprocess_exec'


class TestResolveStream:
    @pytest.mark.anyio
    async def test_returns_track(self, mock_subprocess):
        stdout = b'https://stream.url/audio\nTest Song\nTest Artist\n240\nhttps://thumb.jpg\nhttps://youtube.com/watch?v=abc\n'

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        track = await YtDlpAudioService.resolve_stream(
            'https://youtube.com/watch?v=abc', **_REQUESTER
        )

        assert track.title == 'Test Song'
        assert track.author == 'Test Artist'
        assert track.stream_url == 'https://stream.url/audio'
        assert track.url == 'https://youtube.com/watch?v=abc'
        assert track.duration == 240
        assert track.thumbnail == 'https://thumb.jpg'
        assert track.requested_by == 'TestUser'

    @pytest.mark.anyio
    async def test_fills_defaults_for_empty_fields(self, mock_subprocess):
        stdout = b'https://stream.url/audio\n\n\nNA\n\nhttps://youtube.com/watch?v=abc\n'

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        track = await YtDlpAudioService.resolve_stream('query', **_REQUESTER)

        assert track.title == 'Desconhecido'
        assert track.author == 'Desconhecido'
        assert track.duration == 0

    @pytest.mark.anyio
    async def test_raises_on_failure(self, mock_subprocess):
        mock_subprocess(_SUBPROCESS_TARGET, calls=[(b'', b'ERROR: not found', 1)])

        with pytest.raises(ExternalServiceError) as exc_info:
            await YtDlpAudioService.resolve_stream('bad-url', **_REQUESTER)

        assert exc_info.value.user_message == 'Nao consegui carregar essa musica'

    @pytest.mark.anyio
    async def test_raises_on_insufficient_lines(self, mock_subprocess):
        stdout = b'https://stream.url/audio\nTitle\n'

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        with pytest.raises(ExternalServiceError) as exc_info:
            await YtDlpAudioService.resolve_stream('query', **_REQUESTER)

        assert exc_info.value.user_message == 'Nao consegui obter informacoes dessa musica'


class TestSearch:
    @pytest.mark.anyio
    async def test_returns_tracks(self, mock_subprocess):
        stdout = (
            b'abc123\nSong A\nArtist A\n180\nhttps://thumb-a.jpg\n'
            b'def456\nSong B\nArtist B\n200\nhttps://thumb-b.jpg\n'
        )

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        tracks = await YtDlpAudioService.search('test query', **_REQUESTER)

        assert len(tracks) == 2
        assert tracks[0].title == 'Song A'
        assert tracks[0].url == 'https://www.youtube.com/watch?v=abc123'
        assert tracks[0].stream_url == ''
        assert tracks[1].title == 'Song B'

    @pytest.mark.anyio
    async def test_raises_on_failure(self, mock_subprocess):
        mock_subprocess(_SUBPROCESS_TARGET, calls=[(b'', b'ERROR', 1)])

        with pytest.raises(ExternalServiceError) as exc_info:
            await YtDlpAudioService.search('query', **_REQUESTER)

        assert exc_info.value.user_message == 'Nao consegui buscar musicas'

    @pytest.mark.anyio
    async def test_ignores_incomplete_chunks(self, mock_subprocess):
        stdout = b'abc123\nSong A\nArtist A\n180\nhttps://thumb-a.jpg\ndef456\nSong B\n'

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        tracks = await YtDlpAudioService.search('query', **_REQUESTER)

        assert len(tracks) == 1


class TestResolvePlaylist:
    @pytest.mark.anyio
    async def test_returns_tracks(self, mock_subprocess):
        stdout = (
            b'vid1\nSong 1\nArtist 1\n120\nhttps://t1.jpg\n'
            b'vid2\nSong 2\nArtist 2\n240\nhttps://t2.jpg\n'
            b'vid3\nSong 3\nArtist 3\n300\nhttps://t3.jpg\n'
        )

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(stdout, b'', 0)])

        tracks = await YtDlpAudioService.resolve_playlist(
            'https://youtube.com/playlist?list=PLabc', **_REQUESTER
        )

        assert len(tracks) == 3
        assert tracks[0].url == 'https://www.youtube.com/watch?v=vid1'
        assert tracks[2].duration == 300

    @pytest.mark.anyio
    async def test_limits_to_max_tracks(self, mock_subprocess):
        lines = b''.join(
            f'vid{i}\nSong {i}\nArtist\n100\nhttps://t.jpg\n'.encode() for i in range(250)
        )

        mock_subprocess(_SUBPROCESS_TARGET, calls=[(lines, b'', 0)])

        tracks = await YtDlpAudioService.resolve_playlist('url', **_REQUESTER)

        assert len(tracks) == YtDlpAudioService.MAX_PLAYLIST_TRACKS

    @pytest.mark.anyio
    async def test_raises_on_failure(self, mock_subprocess):
        mock_subprocess(_SUBPROCESS_TARGET, calls=[(b'', b'ERROR', 1)])

        with pytest.raises(ExternalServiceError) as exc_info:
            await YtDlpAudioService.resolve_playlist('url', **_REQUESTER)

        assert exc_info.value.user_message == 'Nao consegui carregar essa playlist'


class TestParseDuration:
    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            ('240', 240),
            ('180.5', 180),
            ('0', 0),
            ('NA', 0),
            ('', 0),
        ],
    )
    def test_parse_duration(self, raw, expected):
        assert YtDlpAudioService._parse_duration(raw) == expected
