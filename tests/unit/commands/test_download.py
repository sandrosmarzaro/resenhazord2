import pytest

from bot.domain.commands.download import DownloadCommand
from bot.domain.models.message import TextContent, VideoBufferContent
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

    @pytest.mark.anyio
    async def test_ytdlp_error_returns_text(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: not found', 1),
            ],
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Não consegui baixar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_subprocess_exception_returns_text(self, command, mocker):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mocker.patch(
            'bot.domain.commands.download.asyncio.create_subprocess_exec',
            side_effect=FileNotFoundError('yt-dlp not found'),
        )

        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'Não consegui baixar' in messages[0].content.text
