import httpx
import pytest

from bot.domain.exceptions import VoiceNoteError
from bot.domain.models.message import (
    AudioBufferContent,
    AudioContent,
    BotMessage,
    ImageBufferContent,
)
from bot.domain.services.voice_note import VoiceNote

FFMPEG = 'bot.domain.services.voice_note.asyncio.create_subprocess_exec'
VOICE = AudioBufferContent(data=b'ogg', mimetype=VoiceNote.MIMETYPE)


def status(content) -> BotMessage:
    return BotMessage(jid='g@g.us', content=content, group_status=True)


class TestForStatus:
    @pytest.mark.anyio
    async def test_encodes_status_audio_as_an_opus_voice_note(self, mock_subprocess):
        ffmpeg = mock_subprocess(FFMPEG, calls=[(b'ogg', b'', 0)])

        message = await VoiceNote.for_status(status(AudioBufferContent(data=b'mp3')))

        args = ffmpeg.call_args.args
        assert message.content == VOICE
        assert (args[:4], args[5:]) == (
            ('ffmpeg', '-v', 'error', '-i'),
            (
                '-vn',
                '-ac',
                '1',
                '-ar',
                '48000',
                '-c:a',
                'libopus',
                '-b:a',
                '64k',
                '-f',
                'ogg',
                'pipe:1',
            ),
        )

    @pytest.mark.anyio
    async def test_downloads_status_audio_from_its_url_first(self, mock_subprocess, respx_mock):
        respx_mock.get('https://cdn.example.com/song.mp3').mock(
            return_value=httpx.Response(200, content=b'mp3')
        )
        mock_subprocess(FFMPEG, calls=[(b'ogg', b'', 0)])

        message = await VoiceNote.for_status(
            status(AudioContent(url='https://cdn.example.com/song.mp3'))
        )

        assert message.content == VOICE

    @pytest.mark.anyio
    async def test_leaves_chat_audio_alone(self, mock_subprocess):
        ffmpeg = mock_subprocess(FFMPEG, calls=[])
        audio = AudioBufferContent(data=b'mp3')

        message = await VoiceNote.for_status(BotMessage(jid='g@g.us', content=audio))

        assert message.content is audio
        ffmpeg.assert_not_called()

    @pytest.mark.anyio
    async def test_leaves_other_status_media_alone(self, mock_subprocess):
        ffmpeg = mock_subprocess(FFMPEG, calls=[])
        image = ImageBufferContent(data=b'jpg', view_once=False)

        message = await VoiceNote.for_status(status(image))

        assert message.content is image
        ffmpeg.assert_not_called()


class TestErrors:
    @pytest.mark.anyio
    async def test_raises_when_ffmpeg_cannot_encode(self, mock_subprocess):
        mock_subprocess(FFMPEG, calls=[(b'', b'Invalid data found', 1)])
        message = status(AudioBufferContent(data=b'not audio'))

        with pytest.raises(VoiceNoteError):
            await VoiceNote.for_status(message)
