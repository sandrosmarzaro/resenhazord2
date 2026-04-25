import pytest

from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig, CommandScope, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from tests.factories.command_data import GroupCommandDataFactory


class PublicCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='pub')

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        from bot.domain.builders.reply import Reply

        return [Reply.to(data).text('public ok')]


class DisabledCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='off', scope=CommandScope.DISABLED)

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


class DevOnlyCommand(Command):
    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='devonly', scope=CommandScope.DEV)

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        from bot.domain.builders.reply import Reply

        return [Reply.to(data).text('dev ok')]


@pytest.fixture
def registry():
    r = CommandRegistry.instance()
    r.register(PublicCommand())
    r.register(DisabledCommand())
    r.register(DevOnlyCommand())
    return r


@pytest.fixture
def handler(registry, mock_dev_list):
    return CommandHandler(registry=registry, dev_list=mock_dev_list)


class TestScopeEnforcement:
    @pytest.mark.anyio
    async def test_public_command_executes_normally(self, handler):
        data = GroupCommandDataFactory.build(text=', pub')

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == 'public ok'

    @pytest.mark.anyio
    async def test_disabled_command_returns_disabled_message(self, handler):
        data = GroupCommandDataFactory.build(text=', off')

        result = await handler.handle(data)

        assert result is not None
        assert 'desativado' in result[0].content.text

    @pytest.mark.anyio
    async def test_dev_command_blocks_non_dev(self, handler, mock_dev_list):
        mock_dev_list.is_dev.return_value = False
        data = GroupCommandDataFactory.build(text=', devonly')

        result = await handler.handle(data)

        assert result is not None
        assert 'desenvolvedores' in result[0].content.text

    @pytest.mark.anyio
    async def test_dev_command_allows_dev(self, handler, mock_dev_list):
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory.build(text=', devonly')

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == 'dev ok'

    @pytest.mark.anyio
    async def test_no_match_returns_none(self, handler):
        data = GroupCommandDataFactory.build(text=', unknown')

        result = await handler.handle(data)

        assert result is None


class TestBatch:
    @pytest.mark.anyio
    async def test_batch_repeats_for_dev(self, handler, mock_dev_list):
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory.build(text=', pub 3x')

        result = await handler.handle(data)

        assert result is not None
        assert len(result) == 3
        assert all(m.content.text == 'public ok' for m in result)

    @pytest.mark.anyio
    async def test_batch_ignored_for_non_dev(self, handler, mock_dev_list):
        mock_dev_list.is_dev.return_value = False
        data = GroupCommandDataFactory.build(text=', pub 3x')

        result = await handler.handle(data)

        assert result is not None
        assert len(result) == 1

    @pytest.mark.anyio
    async def test_batch_capped_at_max(self, handler, mock_dev_list):
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory.build(text=', pub 99x')

        result = await handler.handle(data)

        assert result is not None
        assert len(result) == 5

    @pytest.mark.anyio
    async def test_no_batch_suffix_runs_once(self, handler):
        data = GroupCommandDataFactory.build(text=',pub')

        result = await handler.handle(data)

        assert result is not None


class TestAgentDetection:
    @pytest.mark.anyio
    async def test_agent_trigger_in_dm(self, handler):
        """Test that any message in DM triggers agent mode."""
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text='me mande um yugioh',
            jid='test@s.whatsapp.net',
            sender_jid='test@s.whatsapp.net',
            is_group=False,
        )

        is_agent = handler._is_agent_mention(data)

        assert is_agent is True

    @pytest.mark.anyio
    async def test_agent_trigger_with_send_me_pattern(self, handler):
        """Test that 'mande um' pattern triggers agent in group."""
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text='me mande um pacotinho de yugioh',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        is_agent = handler._is_agent_mention(data)

        assert is_agent is True

    @pytest.mark.anyio
    async def test_no_agent_for_plain_command_in_group(self, handler):
        """Test that plain comma command in group doesn't trigger agent."""
        data = GroupCommandDataFactory.build(text=',pub')

        is_agent = handler._is_agent_mention(data)

        assert is_agent is False
