import pytest

from bot.adapters.discord.music.queue import LoopMode
from bot.adapters.discord.music.views import NowPlayingView
from bot.adapters.discord.music.voice_manager import VoiceManager
from bot.domain.models.track import Track

pytestmark = pytest.mark.anyio


def _track(index: int = 0) -> Track:
    return Track(
        title=f'Song {index}',
        author='Artist',
        url=f'https://youtube.com/watch?v={index}',
        stream_url=f'https://stream/{index}',
        duration=180,
        thumbnail=f'https://thumb/{index}.jpg',
        requested_by='User',
        requested_by_id=1,
    )


@pytest.fixture
def voice_manager(mocker):
    vm = mocker.MagicMock(spec=VoiceManager)
    queue = mocker.MagicMock()
    queue.current = _track()
    queue.volume = 0.5
    queue.current_index = 0
    queue.size = 1
    queue.loop_mode = LoopMode.OFF
    vm.get_queue.return_value = queue
    vm.get_voice_client.return_value = mocker.MagicMock()
    return vm


class TestNowPlayingViewStructure:
    def test_has_expected_buttons(self, voice_manager):
        view = NowPlayingView(voice_manager, guild_id=1)

        labels = [item.label for item in view.children if hasattr(item, 'label')]

        assert 'Pausar' in labels
        assert 'Parar' in labels
        assert 'Repetir' in labels
        assert 'Shuffle' in labels
        assert 'Fila' in labels

    def test_has_two_rows(self, voice_manager):
        view = NowPlayingView(voice_manager, guild_id=1)

        rows = {item.row for item in view.children if hasattr(item, 'row')}

        assert 0 in rows
        assert 1 in rows

    def test_no_timeout(self, voice_manager):
        view = NowPlayingView(voice_manager, guild_id=1)

        assert view.timeout is None


class TestPauseResumeButton:
    async def test_pause_toggles_to_resume(self, voice_manager, mocker):
        vc = voice_manager.get_voice_client.return_value
        vc.is_paused.return_value = False

        view = NowPlayingView(voice_manager, guild_id=1)
        button = view.pause_resume_button

        interaction = mocker.AsyncMock()
        await view.pause_resume_button.callback(interaction)

        vc.pause.assert_called_once()
        assert button.label == 'Retomar'

    async def test_resume_toggles_to_pause(self, voice_manager, mocker):
        vc = voice_manager.get_voice_client.return_value
        vc.is_paused.return_value = True

        view = NowPlayingView(voice_manager, guild_id=1)

        interaction = mocker.AsyncMock()
        await view.pause_resume_button.callback(interaction)

        vc.resume.assert_called_once()
        assert view.pause_resume_button.label == 'Pausar'


class TestStopButton:
    async def test_stop_deletes_message(self, voice_manager, mocker):
        voice_manager.stop = mocker.AsyncMock()
        view = NowPlayingView(voice_manager, guild_id=1)

        interaction = mocker.AsyncMock()
        await view.stop_button.callback(interaction)

        voice_manager.stop.assert_awaited_once_with(1)
        interaction.message.delete.assert_awaited_once()


class TestShuffleButton:
    async def test_shuffles_queue(self, voice_manager, mocker):
        view = NowPlayingView(voice_manager, guild_id=1)

        interaction = mocker.AsyncMock()
        await view.shuffle_button.callback(interaction)

        voice_manager.get_queue.return_value.shuffle.assert_called_once()
        interaction.response.send_message.assert_awaited_once()


class TestQueueButton:
    async def test_sends_queue_view(self, voice_manager, mocker):
        queue = voice_manager.get_queue.return_value
        queue.is_empty = False
        queue.size = 3
        queue.tracks = [_track(i) for i in range(3)]

        view = NowPlayingView(voice_manager, guild_id=1)

        interaction = mocker.AsyncMock()
        await view.queue_button.callback(interaction)

        interaction.response.send_message.assert_awaited_once()
        call_kwargs = interaction.response.send_message.call_args[1]
        assert call_kwargs['ephemeral'] is True
        assert call_kwargs.get('view') is not None


class TestLoopButton:
    async def test_cycles_loop_mode(self, voice_manager, mocker):
        queue = voice_manager.get_queue.return_value
        queue.cycle_loop.return_value = LoopMode.TRACK

        view = NowPlayingView(voice_manager, guild_id=1)

        interaction = mocker.AsyncMock()
        await view.loop_button.callback(interaction)

        queue.cycle_loop.assert_called_once()
        assert 'Musica' in view.loop_button.label
