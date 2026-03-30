import pytest

from bot.adapters.discord.music.queue import MusicQueue
from bot.adapters.discord.music.views import QueueView, TrackActionView
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
def queue_with_tracks():
    queue = MusicQueue()
    for i in range(15):
        queue.add(_track(index=i))
    return queue


@pytest.fixture
def mock_vm(mocker, queue_with_tracks):
    vm = mocker.MagicMock(spec=VoiceManager)
    vm.get_queue.return_value = queue_with_tracks
    return vm


class TestQueueViewStructure:
    def test_has_navigation_buttons(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1)

        button_emojis = [
            str(item.emoji)
            for item in view.children
            if hasattr(item, 'emoji') and item.emoji
        ]

        assert '◀' in button_emojis
        assert '▶' in button_emojis

    def test_prev_disabled_on_first_page(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1, page=0)

        assert view.prev_page_button.disabled is True

    def test_next_enabled_when_more_pages(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1, page=0)

        assert view.next_page_button.disabled is False

    def test_timeout(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1)

        assert view.timeout == 120


class TestQueueViewNavigation:
    async def test_next_page(self, mock_vm, mocker):
        view = QueueView(mock_vm, guild_id=1, page=0)
        interaction = mocker.AsyncMock()

        await view.next_page_button.callback(interaction)

        assert view._page == 1
        interaction.response.edit_message.assert_awaited_once()

    async def test_prev_page(self, mock_vm, mocker):
        view = QueueView(mock_vm, guild_id=1, page=1)
        interaction = mocker.AsyncMock()

        await view.prev_page_button.callback(interaction)

        assert view._page == 0
        interaction.response.edit_message.assert_awaited_once()


class TestQueueViewSelect:
    def test_refresh_select_options(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1)
        view.refresh_select_options()

        options = view.track_select.options

        assert len(options) == 10
        assert options[0].label.startswith('1.')
        assert options[9].label.startswith('10.')

    def test_refresh_select_page_2(self, mock_vm):
        view = QueueView(mock_vm, guild_id=1, page=1)
        view.refresh_select_options()

        options = view.track_select.options

        assert len(options) == 5
        assert options[0].label.startswith('11.')


class TestTrackActionView:
    def test_has_action_buttons(self, mock_vm):
        parent = QueueView(mock_vm, guild_id=1)
        view = TrackActionView(mock_vm, guild_id=1, track_index=2, parent=parent)

        labels = [item.label for item in view.children if hasattr(item, 'label')]

        assert 'Remover' in labels
        assert 'Mover pro topo' in labels
        assert 'Mover pro final' in labels

    async def test_remove(self, mock_vm, queue_with_tracks, mocker):
        parent = QueueView(mock_vm, guild_id=1)
        parent.message = mocker.AsyncMock()
        view = TrackActionView(mock_vm, guild_id=1, track_index=5, parent=parent)

        interaction = mocker.AsyncMock()
        await view.remove_button.callback(interaction)

        assert queue_with_tracks.size == 14
        interaction.response.edit_message.assert_awaited_once()

    async def test_move_to_top(self, mock_vm, queue_with_tracks, mocker):
        parent = QueueView(mock_vm, guild_id=1)
        parent.message = mocker.AsyncMock()
        view = TrackActionView(mock_vm, guild_id=1, track_index=5, parent=parent)

        interaction = mocker.AsyncMock()
        await view.move_top_button.callback(interaction)

        assert queue_with_tracks.tracks[1].title == 'Song 5'

    async def test_move_to_bottom(self, mock_vm, queue_with_tracks, mocker):
        parent = QueueView(mock_vm, guild_id=1)
        parent.message = mocker.AsyncMock()
        view = TrackActionView(mock_vm, guild_id=1, track_index=1, parent=parent)

        interaction = mocker.AsyncMock()
        await view.move_bottom_button.callback(interaction)

        assert queue_with_tracks.tracks[-1].title == 'Song 1'
