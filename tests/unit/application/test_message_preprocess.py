import httpx
import pytest
import respx

from bot.application.message_preprocess import preprocess_for_telegram, preprocess_messages
from bot.domain.models.contents.audio_content import AudioBufferContent, AudioContent
from bot.domain.models.contents.image_content import ImageBufferContent, ImageContent
from bot.domain.models.contents.raw_content import RawContent
from bot.domain.models.contents.video_content import VideoBufferContent, VideoContent
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient

JID = '123@s.whatsapp.net'
AUDIO_URL = 'https://example.com/song.mp3'
IMAGE_URL = 'https://example.com/pic.jpg'
VIDEO_URL = 'https://example.com/clip.mp4'


@pytest.fixture(autouse=True)
def reset_client():
    HttpClient.reset()
    yield
    HttpClient.reset()


def _msg(content):
    return BotMessage(jid=JID, content=content)


class TestPreprocessMessages:
    @pytest.mark.anyio
    async def test_downloads_audio_url_into_buffer(self):
        with respx.mock() as mock:
            mock.get(AUDIO_URL).respond(200, content=b'mp3-bytes')

            result = await preprocess_messages([_msg(AudioContent(url=AUDIO_URL))])

        assert isinstance(result[0].content, AudioBufferContent)
        assert result[0].content.data == b'mp3-bytes'

    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_falls_back_to_original_on_download_failure(self):
        with respx.mock() as mock:
            mock.get(AUDIO_URL).mock(side_effect=httpx.ConnectError('boom'))

            result = await preprocess_messages([_msg(AudioContent(url=AUDIO_URL))])

        assert isinstance(result[0].content, AudioContent)

    @pytest.mark.anyio
    async def test_passes_through_unrelated_content_untouched(self):
        video = VideoContent(url=VIDEO_URL)

        result = await preprocess_messages([_msg(video)])

        assert result[0].content is video


class TestPreprocessForTelegram:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_downloads_video_url_into_buffer(self):
        with respx.mock() as mock:
            mock.get(VIDEO_URL).respond(200, content=b'mp4-bytes')

            result = await preprocess_for_telegram(
                [_msg(VideoContent(url=VIDEO_URL, caption='cap'))]
            )

        assert isinstance(result[0].content, VideoBufferContent)
        assert result[0].content.data == b'mp4-bytes'
        assert result[0].content.caption == 'cap'

    @pytest.mark.anyio
    async def test_raw_video_becomes_video_buffer(self):
        with respx.mock() as mock:
            mock.get(VIDEO_URL).respond(200, content=b'mp4-bytes')

            result = await preprocess_for_telegram(
                [_msg(RawContent(content={'video': {'url': VIDEO_URL}, 'caption': 'cap'}))]
            )

        assert isinstance(result[0].content, VideoBufferContent)
        assert result[0].content.gif_playback is False
        assert result[0].content.caption == 'cap'

    @pytest.mark.anyio
    async def test_raw_image_with_gif_playback_becomes_animation(self):
        with respx.mock() as mock:
            mock.get(IMAGE_URL).respond(200, content=b'gif-bytes')

            result = await preprocess_for_telegram(
                [_msg(RawContent(content={'image': {'url': IMAGE_URL}, 'gifPlayback': True}))]
            )

        content = result[0].content
        assert isinstance(content, VideoBufferContent)
        assert content.gif_playback is True

    @pytest.mark.anyio
    async def test_raw_image_without_gif_playback_becomes_image_buffer(self):
        with respx.mock() as mock:
            mock.get(IMAGE_URL).respond(200, content=b'png-bytes')

            result = await preprocess_for_telegram(
                [_msg(RawContent(content={'image': {'url': IMAGE_URL}}))]
            )

        assert isinstance(result[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_still_runs_shared_image_preprocess(self):
        with respx.mock() as mock:
            mock.get(IMAGE_URL).respond(200, content=b'png-bytes')

            result = await preprocess_for_telegram([_msg(ImageContent(url=IMAGE_URL))])

        assert isinstance(result[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_raw_without_usable_url_is_preserved(self):
        raw = RawContent(content={'unexpected': 1})

        result = await preprocess_for_telegram([_msg(raw)])

        assert result[0].content is raw

    @pytest.mark.anyio(backends=['asyncio'])
    async def test_falls_back_to_raw_on_download_failure(self):
        raw = RawContent(content={'video': {'url': VIDEO_URL}})
        with respx.mock() as mock:
            mock.get(VIDEO_URL).mock(side_effect=httpx.ConnectError('boom'))

            result = await preprocess_for_telegram([_msg(raw)])

        assert result[0].content is raw
