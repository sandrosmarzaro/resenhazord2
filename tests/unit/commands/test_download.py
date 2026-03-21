import pytest

from bot.domain.commands.download import DownloadCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.message import VideoBufferContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return DownloadCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',dl https://youtube.com/watch?v=abc', True),
            (', dl https://youtube.com/watch?v=abc', True),
            (', DL https://youtube.com/watch?v=abc', True),
            (', baixar https://instagram.com/reel/abc', True),
            (', dl http://example.com/video', True),
            (',dl', False),
            ('dl https://youtube.com', False),
            ('hello', False),
            (', dl no-url-here', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_video_buffer(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Test Video Title\n', b'', 0),
                (b'fake-video-data', b'', 0),
            ],
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, VideoBufferContent)
        assert messages[0].content.caption == 'Test Video Title'

    @pytest.mark.anyio
    async def test_video_data_is_buffer(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'\x00\x01\x02video', b'', 0),
            ],
        )

        messages = await command.run(data)

        assert messages[0].content.data == b'\x00\x01\x02video'

    @pytest.mark.anyio
    async def test_extracts_url_from_text(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(
            text=',dl check this https://tiktok.com/@user/video/123 nice'
        )
        mock_exec = mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'TikTok\n', b'', 0),
                (b'data', b'', 0),
            ],
        )

        await command.run(data)

        first_call_args = mock_exec.call_args_list[0][0]
        assert 'https://tiktok.com/@user/video/123' in first_call_args

    @pytest.mark.anyio
    async def test_empty_title_defaults_to_video(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://example.com/v')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'\n', b'', 0),
                (b'data', b'', 0),
            ],
        )

        messages = await command.run(data)

        assert messages[0].content.caption == 'Vídeo'


class TestErrors:
    @pytest.mark.anyio
    async def test_generic_ytdlp_error(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: not found', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'Não consegui baixar' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_no_video_in_post(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: There is no video in this post', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'não tem vídeo' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_private_video(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: Private video', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'privado' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_video_unavailable(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: Video unavailable', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'não está disponível' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_age_restricted(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: Sign in to confirm your age', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'restrição de idade' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_forbidden(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'HTTP Error 403: Forbidden', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'bloqueado' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_subprocess_exception(self, command, mocker):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mocker.patch(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            side_effect=FileNotFoundError('yt-dlp not found'),
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'Não consegui baixar' in exc_info.value.user_message
