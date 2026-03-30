import asyncio

import pytest

from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.domain.models.track import Track

pytestmark = pytest.mark.anyio


def _track(title: str = 'Song', index: int = 0) -> Track:
    return Track(
        title=f'{title} {index}',
        author='Artist',
        url=f'https://youtube.com/watch?v={index}',
        stream_url=f'https://stream/{index}',
        duration=180,
        thumbnail=f'https://thumb/{index}.jpg',
        requested_by='User',
        requested_by_id=1,
    )


@pytest.fixture
def voice_manager():
    return VoiceManager()


@pytest.fixture
def mock_voice_client(mocker):
    vc = mocker.MagicMock()
    vc.is_connected.return_value = True
    vc.is_playing.return_value = False
    vc.channel = mocker.MagicMock()
    vc.channel.id = 100
    vc.play = mocker.MagicMock()
    vc.stop = mocker.MagicMock()
    vc.disconnect = mocker.AsyncMock()
    vc.move_to = mocker.AsyncMock()
    return vc


@pytest.fixture
def mock_channel(mocker, mock_voice_client):
    channel = mocker.AsyncMock()
    channel.guild.id = 1
    channel.id = 100
    channel.name = 'test-voice'
    channel.connect = mocker.AsyncMock(return_value=mock_voice_client)
    return channel


class TestGetQueue:
    def test_creates_queue_on_first_access(self, voice_manager):
        queue = voice_manager.get_queue(1)

        assert queue is not None
        assert queue.is_empty

    def test_returns_same_queue(self, voice_manager):
        q1 = voice_manager.get_queue(1)
        q2 = voice_manager.get_queue(1)

        assert q1 is q2


class TestEnsureConnected:
    @pytest.mark.anyio
    async def test_connects_to_channel(self, voice_manager, mock_channel, mock_voice_client):
        vc = await voice_manager.ensure_connected(mock_channel)

        assert vc is mock_voice_client
        mock_channel.connect.assert_awaited_once()

    @pytest.mark.anyio
    async def test_reuses_existing_connection(
        self,
        voice_manager,
        mock_channel,
        mock_voice_client,
    ):
        voice_manager._voice_clients[1] = mock_voice_client

        vc = await voice_manager.ensure_connected(mock_channel)

        assert vc is mock_voice_client
        mock_channel.connect.assert_not_awaited()

    @pytest.mark.anyio
    async def test_moves_to_different_channel(
        self,
        voice_manager,
        mock_channel,
        mock_voice_client,
    ):
        mock_voice_client.channel.id = 200
        voice_manager._voice_clients[1] = mock_voice_client

        await voice_manager.ensure_connected(mock_channel)

        mock_voice_client.move_to.assert_awaited_once_with(mock_channel)


class TestPlayTrack:
    @pytest.mark.anyio
    async def test_plays_track(self, voice_manager, mock_voice_client, mocker):
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.FFmpegPCMAudio')
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.PCMVolumeTransformer')
        voice_manager._voice_clients[1] = mock_voice_client
        track = _track()

        await voice_manager.play_track(1, track)

        mock_voice_client.play.assert_called_once()

    @pytest.mark.anyio
    async def test_stops_current_before_playing(self, voice_manager, mock_voice_client, mocker):
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.FFmpegPCMAudio')
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.PCMVolumeTransformer')
        mock_voice_client.is_playing.return_value = True
        voice_manager._voice_clients[1] = mock_voice_client
        track = _track()

        await voice_manager.play_track(1, track)

        mock_voice_client.stop.assert_called_once()

    @pytest.mark.anyio
    async def test_does_nothing_without_voice_client(self, voice_manager):
        track = _track()

        await voice_manager.play_track(1, track)


class TestStop:
    @pytest.mark.anyio
    async def test_clears_queue_and_disconnects(self, voice_manager, mock_voice_client):
        voice_manager._voice_clients[1] = mock_voice_client
        mock_voice_client.is_playing.return_value = True
        queue = voice_manager.get_queue(1)
        queue.add(_track())

        await voice_manager.stop(1)

        assert queue.is_empty
        mock_voice_client.stop.assert_called_once()
        mock_voice_client.disconnect.assert_awaited_once()


class TestSkip:
    @pytest.mark.anyio
    async def test_stops_current_playback(self, voice_manager, mock_voice_client):
        mock_voice_client.is_playing.return_value = True
        voice_manager._voice_clients[1] = mock_voice_client

        await voice_manager.skip(1)

        mock_voice_client.stop.assert_called_once()


class TestDisconnect:
    @pytest.mark.anyio
    async def test_disconnects_and_cleans_up(self, voice_manager, mock_voice_client):
        voice_manager._voice_clients[1] = mock_voice_client
        voice_manager._queues[1] = voice_manager.get_queue(1)

        await voice_manager.disconnect(1)

        mock_voice_client.disconnect.assert_awaited_once()
        assert 1 not in voice_manager._voice_clients
        assert 1 not in voice_manager._queues


class TestIsPlaying:
    def test_returns_true_when_playing(self, voice_manager, mock_voice_client):
        mock_voice_client.is_playing.return_value = True
        voice_manager._voice_clients[1] = mock_voice_client

        assert voice_manager.is_playing(1) is True

    def test_returns_false_when_not_connected(self, voice_manager):
        assert voice_manager.is_playing(1) is False


class TestOnTrackEnd:
    @pytest.mark.anyio
    async def test_advances_and_plays_next(self, voice_manager, mock_voice_client, mocker):
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.FFmpegPCMAudio')
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.PCMVolumeTransformer')
        voice_manager._voice_clients[1] = mock_voice_client
        queue = voice_manager.get_queue(1)
        queue.add(_track(index=0))
        queue.add(_track(index=1))

        await voice_manager._on_track_end(1, None)

        mock_voice_client.play.assert_called_once()

    @pytest.mark.anyio
    async def test_resolves_stream_url_before_playing(
        self, voice_manager, mock_voice_client, mocker
    ):
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.FFmpegPCMAudio')
        mocker.patch('bot.adapters.discord.music.voice_manager.discord.PCMVolumeTransformer')
        voice_manager._voice_clients[1] = mock_voice_client

        resolved = _track(title='Resolved', index=1)
        mock_resolve = mocker.patch(
            'bot.adapters.discord.music.voice_manager.YtDlpAudioService.resolve_stream',
            new_callable=mocker.AsyncMock,
            return_value=resolved,
        )

        unresolved = Track(
            title='Unresolved 1',
            author='Artist',
            url='https://youtube.com/watch?v=1',
            stream_url='',
            duration=180,
            thumbnail='',
            requested_by='User',
            requested_by_id=1,
        )
        queue = voice_manager.get_queue(1)
        queue.add(_track(index=0))
        queue.add(unresolved)

        await voice_manager._on_track_end(1, None)

        mock_resolve.assert_awaited_once_with(
            unresolved.url,
            requested_by='User',
            requested_by_id=1,
        )
        mock_voice_client.play.assert_called_once()
        assert queue.current.title == 'Resolved 1'

    @pytest.mark.anyio
    async def test_skips_track_on_resolve_failure(self, voice_manager, mocker):
        from bot.domain.exceptions import ExternalServiceError

        mocker.patch(
            'bot.adapters.discord.music.voice_manager.YtDlpAudioService.resolve_stream',
            new_callable=mocker.AsyncMock,
            side_effect=ExternalServiceError('fail'),
        )
        mock_sleep = mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        unresolved = Track(
            title='Unresolved',
            author='Artist',
            url='https://youtube.com/watch?v=1',
            stream_url='',
            duration=180,
            thumbnail='',
            requested_by='User',
            requested_by_id=1,
        )
        queue = voice_manager.get_queue(1)
        queue.add(_track(index=0))
        queue.add(unresolved)

        await voice_manager._on_track_end(1, None)

        assert 1 in voice_manager._disconnect_tasks
        await asyncio.sleep(0)
        mock_sleep.assert_awaited()

    @pytest.mark.anyio
    async def test_schedules_disconnect_at_queue_end(self, voice_manager, mocker):
        queue = voice_manager.get_queue(1)
        queue.add(_track(index=0))
        mock_sleep = mocker.patch('asyncio.sleep', new_callable=mocker.AsyncMock)

        await voice_manager._on_track_end(1, None)

        assert 1 in voice_manager._disconnect_tasks
        await asyncio.sleep(0)
        mock_sleep.assert_awaited()
