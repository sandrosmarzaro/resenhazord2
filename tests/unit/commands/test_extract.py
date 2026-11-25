import io

import pytest
from PIL import Image

from bot.domain.commands.extract import ExtractCommand
from bot.domain.services.sticker.sticker_video import StickerVideo
from tests.factories.command_data import GroupCommandDataFactory

MESSAGE_ID = 'MSG_99'


def _make_webp(*, animated: bool = False) -> bytes:
    if animated:
        frames = [Image.new('RGBA', (10, 10), color) for color in ['red', 'blue']]
        output = io.BytesIO()
        frames[0].save(output, format='WEBP', save_all=True, append_images=frames[1:])
        return output.getvalue()
    img = Image.new('RGBA', (10, 10), 'red')
    output = io.BytesIO()
    img.save(output, format='WEBP')
    return output.getvalue()


@pytest.fixture
def command(mock_whatsapp):
    cmd = ExtractCommand()
    cmd._whatsapp = mock_whatsapp
    return cmd


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',extrair', True),
            (', extrair', True),
            (', EXTRAIR', True),
            (',extrair mute', True),
            ('extrair', False),
            ('hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestNoSticker:
    @pytest.mark.anyio
    async def test_no_media(self, command):
        data = GroupCommandDataFactory.build(text=',extrair')

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'sticker' in messages[0].content.text

    @pytest.mark.anyio
    async def test_non_sticker_media(self, command):
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='image',
            media_source='quoted',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'sticker' in messages[0].content.text

    @pytest.mark.anyio
    async def test_direct_sticker_rejected(self, command):
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='direct',
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'sticker' in messages[0].content.text


class TestStaticSticker:
    @pytest.mark.anyio
    async def test_converts_in_a_worker_thread(self, command, mock_whatsapp, pillow_threads):
        mock_whatsapp.download_media.return_value = _make_webp(animated=False)
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=False,
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        assert pillow_threads
        assert not any(pillow_threads)

    @pytest.mark.anyio
    async def test_converts_to_png(self, command, mock_whatsapp):
        webp_data = _make_webp(animated=False)
        mock_whatsapp.download_media.return_value = webp_data
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=False,
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'image_buffer'
        assert messages[0].content.view_once is False
        img = Image.open(io.BytesIO(messages[0].content.data))
        assert img.format == 'PNG'

    @pytest.mark.anyio
    async def test_calls_download_media(self, command, mock_whatsapp):
        mock_whatsapp.download_media.return_value = _make_webp()
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            message_id=MESSAGE_ID,
        )

        await command.run(data)

        mock_whatsapp.download_media.assert_called_once_with(MESSAGE_ID, 'quoted')


class TestAnimatedSticker:
    @pytest.fixture(autouse=True)
    def silent(self, mocker):
        return mocker.patch.object(StickerVideo, 'silent', return_value=b'silent-mp4')

    @pytest.mark.anyio
    async def test_sends_the_animation_as_a_looping_mp4(self, command, silent):
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_buffer=_make_webp(animated=True),
        )

        messages = await command.run(data)

        frames = silent.await_args.args[0]
        content = messages[0].content
        assert (frames[:6], content.data, content.gif_playback) == (b'GIF89a', b'silent-mp4', True)

    @pytest.mark.anyio
    async def test_converts_to_gif_video(self, command, mock_whatsapp):
        webp_data = _make_webp(animated=True)
        mock_whatsapp.download_media.return_value = webp_data
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=True,
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'video_buffer'
        assert messages[0].content.gif_playback is True
        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_detects_the_animation_a_web_quote_drops(self, command):
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=False,
            media_buffer=_make_webp(animated=True),
        )

        messages = await command.run(data)

        assert messages[0].content.gif_playback is True


class TestAudioSticker:
    AUDIO = b'ogg-opus'

    @pytest.fixture
    def render(self, mocker):
        return mocker.patch.object(StickerVideo, 'render', return_value=b'mp4')

    def _quoting(self, *, animated: bool = True, text: str = ',extrair'):
        return GroupCommandDataFactory.build(
            text=text,
            media_type='sticker',
            media_source='quoted',
            media_buffer=_make_webp(animated=animated),
            media_audio=self.AUDIO,
        )

    @pytest.mark.anyio
    async def test_sends_a_video_with_sound(self, command, render):
        messages = await command.run(self._quoting())

        content = messages[0].content
        assert (content.type, content.data, content.gif_playback) == ('video_buffer', b'mp4', False)

    @pytest.mark.anyio
    async def test_loops_the_animation_under_the_audio(self, command, render):
        await command.run(self._quoting(animated=True))

        frames, audio = render.await_args.args
        assert (frames[:6], audio, render.await_args.kwargs) == (
            b'GIF89a',
            self.AUDIO,
            {'animated': True},
        )

    @pytest.mark.anyio
    async def test_holds_a_still_sticker_under_the_audio(self, command, render):
        await command.run(self._quoting(animated=False))

        frames, _ = render.await_args.args
        assert (frames[:8], render.await_args.kwargs) == (b'\x89PNG\r\n\x1a\n', {'animated': False})

    @pytest.mark.anyio
    async def test_mute_sends_the_silent_animation(self, command, render, mocker):
        mocker.patch.object(StickerVideo, 'silent', return_value=b'silent-mp4')

        messages = await command.run(self._quoting(text=',extrair mute'))

        render.assert_not_awaited()
        assert (messages[0].content.data, messages[0].content.gif_playback) == (b'silent-mp4', True)


def _padded_webp(*, animated: bool) -> bytes:
    # What ,stic full makes of a portrait video: 6x10 content on a transparent 20x10.
    frames = []
    for color in ['red', 'blue']:
        frame = Image.new('RGBA', (20, 10), (0, 0, 0, 0))
        frame.paste(Image.new('RGBA', (6, 10), color), (7, 0))
        frames.append(frame)
    output = io.BytesIO()
    if animated:
        frames[0].save(
            output,
            format='WEBP',
            save_all=True,
            append_images=frames[1:],
            duration=[100, 300],
            lossless=True,
        )
    else:
        frames[0].save(output, format='WEBP', lossless=True)
    return output.getvalue()


class TestDelivery:
    @pytest.mark.anyio
    async def test_audio_video_is_not_view_once(self, command, mocker):
        mocker.patch.object(StickerVideo, 'render', return_value=b'mp4')
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_buffer=_make_webp(animated=True),
            media_audio=b'ogg',
        )

        messages = await command.run(data)

        assert messages[0].content.view_once is False


class TestTransparentPadding:
    def _quoting(self, webp: bytes):
        return GroupCommandDataFactory.build(
            text=',extrair', media_type='sticker', media_source='quoted', media_buffer=webp
        )

    @pytest.mark.anyio
    async def test_trims_the_padding_off_an_animation(self, command, mocker):
        silent = mocker.patch.object(StickerVideo, 'silent', return_value=b'mp4')

        await command.run(self._quoting(_padded_webp(animated=True)))

        gif = Image.open(io.BytesIO(silent.await_args.args[0]))
        assert (gif.size, gif.n_frames) == ((6, 10), 2)

    @pytest.mark.anyio
    async def test_keeps_each_frame_duration(self, command, mocker):
        silent = mocker.patch.object(StickerVideo, 'silent', return_value=b'mp4')

        await command.run(self._quoting(_padded_webp(animated=True)))

        gif = Image.open(io.BytesIO(silent.await_args.args[0]))
        durations = []
        for index in range(gif.n_frames):
            gif.seek(index)
            durations.append(gif.info['duration'])
        assert durations == [100, 300]

    @pytest.mark.anyio
    async def test_keeps_a_fully_transparent_sticker_whole(self, command):
        output = io.BytesIO()
        Image.new('RGBA', (20, 10), (0, 0, 0, 0)).save(output, format='WEBP', lossless=True)

        messages = await command.run(self._quoting(output.getvalue()))

        assert Image.open(io.BytesIO(messages[0].content.data)).size == (20, 10)

    @pytest.mark.anyio
    async def test_trims_the_padding_off_a_still(self, command):
        messages = await command.run(self._quoting(_padded_webp(animated=False)))

        assert Image.open(io.BytesIO(messages[0].content.data)).size == (6, 10)


class TestConversionError:
    @pytest.mark.anyio
    async def test_returns_error_on_bad_data(self, command, mock_whatsapp):
        mock_whatsapp.download_media.return_value = b'not-an-image'
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=False,
            message_id=MESSAGE_ID,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert 'extrair' in messages[0].content.text.lower()


class TestProactiveMediaBuffer:
    @pytest.mark.anyio
    async def test_uses_proactive_buffer_skips_download(self, command, mock_whatsapp):
        webp_data = _make_webp(animated=False)
        data = GroupCommandDataFactory.build(
            text=',extrair',
            media_type='sticker',
            media_source='quoted',
            media_is_animated=False,
            message_id=MESSAGE_ID,
            media_buffer=webp_data,
        )

        messages = await command.run(data)

        assert len(messages) == 1
        assert messages[0].content.type == 'image_buffer'
        mock_whatsapp.download_media.assert_not_called()
