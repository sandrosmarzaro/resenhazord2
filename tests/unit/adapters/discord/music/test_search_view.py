import pytest

from bot.adapters.discord.music.views import (
    SearchCancelButton,
    SearchContext,
    SearchResultView,
    SearchSelectButton,
)
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
def mock_vm(mocker):
    vm = mocker.MagicMock(spec=VoiceManager)
    vm.get_queue.return_value = mocker.MagicMock()
    vm.get_queue.return_value.add.return_value = 0
    vm.is_playing.return_value = False
    vm.ensure_connected = mocker.AsyncMock()
    vm.play_track = mocker.AsyncMock()
    return vm


@pytest.fixture
def search_ctx(mock_vm, mocker):
    return SearchContext(
        voice_manager=mock_vm,
        guild_id=1,
        voice_channel=mocker.AsyncMock(),
        text_channel=mocker.AsyncMock(),
        requester_name='User',
        requester_id=1,
    )


class TestSearchResultViewStructure:
    def test_creates_buttons_for_each_track(self, search_ctx):
        tracks = [_track(i) for i in range(3)]

        view = SearchResultView(tracks=tracks, ctx=search_ctx)

        select_buttons = [c for c in view.children if isinstance(c, SearchSelectButton)]
        cancel_buttons = [c for c in view.children if isinstance(c, SearchCancelButton)]

        assert len(select_buttons) == 3
        assert len(cancel_buttons) == 1

    def test_has_timeout(self, search_ctx):
        view = SearchResultView(tracks=[_track()], ctx=search_ctx)

        assert view.timeout == 60


class TestSearchSelection:
    async def test_select_resolves_and_plays(self, mock_vm, search_ctx, mocker):
        mocker.patch(
            'bot.adapters.discord.music.views.YtDlpAudioService.resolve_stream',
            new_callable=mocker.AsyncMock,
            return_value=_track(0),
        )

        view = SearchResultView(tracks=[_track(0)], ctx=search_ctx)

        interaction = mocker.AsyncMock()
        await view.select_track(interaction, 0)

        mock_vm.ensure_connected.assert_awaited_once()
        mock_vm.play_track.assert_awaited_once()


class TestCancelButton:
    async def test_cancel_edits_message(self, mocker):
        button = SearchCancelButton()
        button._view = mocker.MagicMock()

        interaction = mocker.AsyncMock()
        await button.callback(interaction)

        interaction.response.edit_message.assert_awaited_once()
