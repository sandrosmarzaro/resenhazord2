import io

import pytest
from PIL import Image

from bot.domain.commands.extract import ExtractCommand
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
        assert messages[0].content.view_once is True
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
        assert messages[0].content.view_once is True


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
