import pytest

from bot.domain.commands.group_status import GroupStatusCommand
from bot.domain.models.message import (
    AudioBufferContent,
    ImageBufferContent,
    TextContent,
    VideoBufferContent,
)
from bot.domain.services.voice_note import VoiceNote
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


@pytest.fixture
def command(mock_whatsapp):
    cmd = GroupStatusCommand()
    cmd._whatsapp = mock_whatsapp
    return cmd


def quoting(media_type: str, text: str = ',status', caption: str | None = None):
    return GroupCommandDataFactory.build(
        text=text,
        media_type=media_type,
        media_source='quoted',
        media_buffer=b'media',
        media_caption=caption,
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',status', True),
            (', status bom dia', True),
            (', STATUS', True),
            ('status', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestText:
    @pytest.mark.anyio
    async def test_posts_the_given_text(self, command):
        data = GroupCommandDataFactory.build(text=',status bom dia')

        [message] = await command.run(data)

        assert (message.jid, message.content, message.group_status) == (
            data.jid,
            TextContent(text='bom dia'),
            True,
        )

    @pytest.mark.anyio
    async def test_posts_the_quoted_text(self, command):
        data = GroupCommandDataFactory.build(text=',status', quoted_text='frase do dia')

        [message] = await command.run(data)

        assert message.content == TextContent(text='frase do dia')


class TestMedia:
    @pytest.mark.anyio
    async def test_posts_the_quoted_image_with_its_caption(self, command):
        [message] = await command.run(quoting('image', caption='legenda'))

        assert (message.content, message.group_status) == (
            ImageBufferContent(data=b'media', caption='legenda', view_once=False),
            True,
        )

    @pytest.mark.anyio
    async def test_the_given_text_replaces_the_caption(self, command):
        [message] = await command.run(quoting('image', text=',status nova', caption='velha'))

        assert message.content.caption == 'nova'

    @pytest.mark.anyio
    async def test_posts_the_quoted_video(self, command):
        [message] = await command.run(quoting('video'))

        assert message.content == VideoBufferContent(data=b'media', view_once=False)

    @pytest.mark.anyio
    async def test_posts_the_quoted_audio_as_an_opus_voice_note(self, command, mock_subprocess):
        mock_subprocess(
            'bot.domain.services.voice_note.asyncio.create_subprocess_exec',
            calls=[(b'ogg', b'', 0)],
        )

        [message] = await command.run(quoting('audio'))

        assert message.content == AudioBufferContent(data=b'ogg', mimetype=VoiceNote.MIMETYPE)


class TestRefusals:
    @pytest.mark.anyio
    async def test_explains_usage_when_there_is_nothing_to_post(self, command):
        [message] = await command.run(GroupCommandDataFactory.build(text=',status'))

        assert (message.content.text, message.group_status) == (
            GroupStatusCommand.USAGE,
            False,
        )

    @pytest.mark.anyio
    async def test_refuses_a_sticker(self, command):
        [message] = await command.run(quoting('sticker'))

        assert (message.content.text, message.group_status) == (
            GroupStatusCommand.UNSUPPORTED_MEDIA,
            False,
        )

    @pytest.mark.anyio
    async def test_only_works_in_a_group(self, command):
        [message] = await command.run(PrivateCommandDataFactory.build(text=',status oi'))

        assert message.group_status is False
