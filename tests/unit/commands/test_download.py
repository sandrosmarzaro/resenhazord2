from http import HTTPStatus

import httpx
import pytest

from bot.domain.commands.download import DownloadCommand
from bot.domain.exceptions import DownloadError
from bot.domain.models.message import ImageBufferContent, VideoBufferContent
from bot.domain.services.ytdlp import YtDlpService
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
            (',dl', True),
            (',dl show', True),
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'TikTok\n', b'', 0),
                (b'data', b'', 0),
            ],
        )

        await command.run(data)

        first_call_args = mock_exec.call_args_list[0][0]
        assert 'https://tiktok.com/@user/video/123' in first_call_args

    @pytest.mark.anyio
    async def test_limits_to_single_playlist_item(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://x.com/i/status/123')
        mock_exec = mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'video-data', b'', 0),
            ],
        )

        await command.run(data)

        for call in mock_exec.call_args_list:
            assert '--playlist-items' in call[0]
            assert '1' in call[0]

    @pytest.mark.anyio
    async def test_empty_title_defaults_to_video(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://example.com/v')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'\n', b'', 0),
                (b'data', b'', 0),
            ],
        )

        messages = await command.run(data)

        assert messages[0].content.caption == 'Vídeo'


class TestQuotedLink:
    @pytest.mark.anyio
    async def test_downloads_link_from_quoted_message(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(
            text=',dl show', quoted_text=',dl https://instagram.com/reel/abc'
        )
        mock_exec = mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Reel\n', b'', 0),
                (b'video-data', b'', 0),
            ],
        )

        messages = await command.run(data)

        assert 'https://instagram.com/reel/abc' in mock_exec.call_args_list[0][0]
        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_prefers_own_link_over_quoted(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(
            text=',dl https://youtube.com/watch?v=own',
            quoted_text=',dl https://instagram.com/reel/abc',
        )
        mock_exec = mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'video-data', b'', 0),
            ],
        )

        await command.run(data)

        assert 'https://youtube.com/watch?v=own' in mock_exec.call_args_list[0][0]

    @pytest.mark.anyio
    @pytest.mark.parametrize('quoted_text', [None, 'sem link aqui'])
    async def test_asks_for_link_when_none_found(self, command, quoted_text):
        data = GroupCommandDataFactory.build(text=',dl show', quoted_text=quoted_text)

        messages = await command.run(data)

        assert 'Cadê o link' in messages[0].content.text


class TestImagePost:
    IMAGE_URL = 'https://instagram.fvix7-1.fna.fbcdn.net/v/photo.jpg'

    @pytest.fixture
    def image_post(self, mock_subprocess, respx_mock):
        def _factory(image_url: str = self.IMAGE_URL):
            image_route = respx_mock.get(image_url).mock(
                return_value=httpx.Response(HTTPStatus.OK, content=b'fake-image')
            )
            mock_exec = mock_subprocess(
                'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
                calls=[
                    (b'\n', b'', 0),
                    (b'', b'ERROR: [Instagram] abc: There is no video in this post', 1),
                    (f'Post by someone\n{image_url}\n'.encode(), b'', 0),
                ],
            )
            return mock_exec, image_route

        return _factory

    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, image_post):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        image_post()

        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)
        assert messages[0].content.data == b'fake-image'
        assert messages[0].content.caption == 'Post by someone'

    @pytest.mark.anyio
    async def test_reads_thumbnail_ignoring_missing_formats(self, command, image_post):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        mock_exec, _ = image_post()

        await command.run(data)

        image_call_args = mock_exec.call_args_list[2][0]
        assert '--ignore-no-formats-error' in image_call_args
        assert 'thumbnail' in image_call_args

    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'image_url',
        [
            'http://169.254.169.254/latest/meta-data',
            'http://instagram.fvix7-1.fna.fbcdn.net/v/photo.jpg',
            'https://fbcdn.net.evil.com/photo.jpg',
        ],
    )
    async def test_refuses_image_outside_instagram_cdn(self, command, image_post, image_url):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        _, image_route = image_post(image_url)

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert not image_route.called
        assert 'Não consegui baixar' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_image_extraction_error(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'\n', b'', 0),
                (b'', b'ERROR: [Instagram] abc: There is no video in this post', 1),
                (b'', b'ERROR: [Instagram] abc: login required', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'precisa de login' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_refuses_image_over_buffer_limit(self, command, image_post, mocker):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/p/abc')
        image_post()
        mocker.patch.object(YtDlpService, 'MAX_BUFFER', len(b'fake-image') - 1)

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'muito grande' in exc_info.value.user_message


class TestCookies:
    @pytest.mark.anyio
    async def test_passes_cookies_to_both_subprocesses(self, mock_subprocess):
        command = DownloadCommand(cookies_path='/secrets/cookies.txt')
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/reel/abc')
        mock_exec = mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Reel\n', b'', 0),
                (b'video-data', b'', 0),
            ],
        )

        await command.run(data)

        for call in mock_exec.call_args_list:
            assert '--cookies' in call[0]
            assert '/secrets/cookies.txt' in call[0]

    @pytest.mark.anyio
    async def test_omits_cookies_when_unset(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_exec = mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'data', b'', 0),
            ],
        )

        await command.run(data)

        for call in mock_exec.call_args_list:
            assert '--cookies' not in call[0]


class TestErrors:
    @pytest.mark.anyio
    async def test_generic_ytdlp_error(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: not found', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'Não consegui baixar' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_private_video(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
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
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'HTTP Error 403: Forbidden', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'bloqueado' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_no_video_in_tweet(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://x.com/user/status/123')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: [twitter] 123: No video could be found in this tweet', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'não tem vídeo' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_unsupported_url(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://example.com/unknown')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (b'', b'ERROR: Unsupported URL: https://example.com/unknown', 1),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'não é suportado' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_login_required(self, command, mock_subprocess):
        data = GroupCommandDataFactory.build(text=',dl https://instagram.com/reel/abc')
        mock_subprocess(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            calls=[
                (b'Title\n', b'', 0),
                (
                    b'',
                    b'ERROR: [Instagram] abc: login required',
                    1,
                ),
            ],
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'precisa de login' in exc_info.value.user_message

    @pytest.mark.anyio
    async def test_subprocess_exception(self, command, mocker):
        data = GroupCommandDataFactory.build(text=',dl https://youtube.com/watch?v=abc')
        mocker.patch(
            'bot.domain.services.ytdlp.asyncio.create_subprocess_exec',
            side_effect=FileNotFoundError('yt-dlp not found'),
        )

        with pytest.raises(DownloadError) as exc_info:
            await command.run(data)

        assert 'Não consegui baixar' in exc_info.value.user_message
