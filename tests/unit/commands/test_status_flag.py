import pytest

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, Platform
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory


class PhotoCommand(Command):
    def __init__(self) -> None:
        super().__init__()
        self.executed = False

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='foto', flags=[Flag.SHOW], category=Category.RANDOM, platforms=[Platform.ALL]
        )

    @property
    def menu_description(self) -> str:
        return 'Foto.'

    async def execute(self, data, parsed):
        self.executed = True
        return [Reply.to(data).image('https://example.com/foto.jpg', 'legenda')]


@pytest.fixture
def command():
    return PhotoCommand()


class TestConfig:
    def test_a_command_with_show_also_takes_status(self):
        config = CommandConfig(name='foto', flags=[Flag.SHOW])

        assert config.flags == [Flag.SHOW, Flag.STATUS]

    def test_a_command_without_show_does_not(self):
        config = CommandConfig(name='oi', flags=[Flag.DM])

        assert config.flags == [Flag.DM]


class TestInWhatsAppGroup:
    @pytest.mark.anyio
    async def test_marks_the_reply_as_a_group_status(self, command):
        [message] = await command.run(GroupCommandDataFactory.build(text=',foto status'))

        assert message.to_dict()['group_status'] is True

    @pytest.mark.anyio
    async def test_drops_view_once_since_a_status_cannot_be(self, command):
        [message] = await command.run(GroupCommandDataFactory.build(text=',foto status'))

        assert message.content.view_once is False

    @pytest.mark.anyio
    async def test_leaves_the_reply_in_the_chat_without_the_flag(self, command):
        [message] = await command.run(GroupCommandDataFactory.build(text=',foto'))

        assert 'group_status' not in message.to_dict()


class TestOutsideWhatsAppGroup:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        'data',
        [
            PrivateCommandDataFactory.build(text=',foto status'),
            GroupCommandDataFactory.build(text=',foto status', platform=Platform.TELEGRAM),
        ],
        ids=['whatsapp-private', 'telegram-group'],
    )
    async def test_answers_that_status_only_works_in_a_group(self, command, data):
        [message] = await command.run(data)

        assert message.content.text == Command.STATUS_ONLY_IN_GROUPS
        assert command.executed is False
