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
        data = GroupCommandDataFactory.build(text=',pub')

        is_agent = handler._is_agent_mention(data)

        assert is_agent is False

    def test_agent_trigger_by_bot_mention_tag(self, handler):
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text='@resenhazord ver placar',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        assert handler._is_agent_mention(data) is True

    def test_agent_trigger_by_mentioned_jid(self, handler, mocker):
        from bot.domain.models.command_data import CommandData

        mocker.patch(
            'bot.application.command_handler.Settings',
            return_value=mocker.MagicMock(
                resenhazord2_jid='555@s.whatsapp.net',
                resenha_jid='',
                resenhazord2_lid='',
            ),
        )
        handler_with_jid = CommandHandler(registry=handler._registry, dev_list=handler._dev_list)

        data = CommandData(
            text='hello',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            mentioned_jids=['555@s.whatsapp.net'],
            is_group=True,
        )

        assert handler_with_jid._is_agent_mention(data) is True


class TestRunAgent:
    @pytest.mark.anyio
    async def test_run_agent_returns_translated_data(self, handler, mocker):
        from bot.domain.models.command_data import CommandData

        translated = CommandData(
            text=',placar now',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )
        executor_mock = mocker.MagicMock()
        executor_mock.run = mocker.AsyncMock(return_value=translated)
        mocker.patch(
            'bot.application.command_handler.AgentExecutor',
            return_value=executor_mock,
        )

        data = CommandData(
            text='@resenhazord ver placar',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler._run_agent(data)

        assert result.text == ',placar now'

    @pytest.mark.anyio
    async def test_run_agent_value_error_returns_clarify_fallback(self, handler, mocker):
        from bot.domain.constants import CLARIFY_PREFIX
        from bot.domain.models.command_data import CommandData

        executor_mock = mocker.MagicMock()
        executor_mock.run = mocker.AsyncMock(side_effect=ValueError('invalid response'))
        mocker.patch(
            'bot.application.command_handler.AgentExecutor',
            return_value=executor_mock,
        )

        data = CommandData(
            text='@resenhazord ver placar',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler._run_agent(data)

        assert result.text.startswith(CLARIFY_PREFIX)
        assert 'inesperado' in result.text.lower() or 'menu' in result.text.lower()


class TestRunCommand:
    @pytest.mark.anyio
    async def test_bot_error_reraises(self, handler, mocker):
        from bot.domain.exceptions import BotError

        cmd = mocker.MagicMock()
        cmd.run = mocker.AsyncMock(side_effect=BotError('custom'))

        with pytest.raises(BotError, match='custom'):
            await CommandHandler._run_command(cmd, mocker.MagicMock(), 1)

    @pytest.mark.anyio
    async def test_generic_exception_reraises(self, handler, mocker):
        cmd = mocker.MagicMock()
        cmd.run = mocker.AsyncMock(side_effect=RuntimeError('boom'))

        with pytest.raises(RuntimeError, match='boom'):
            await CommandHandler._run_command(cmd, mocker.MagicMock(), 1)


class TestSuggestHandler:
    @pytest.mark.anyio
    async def test_suggest_returns_conversational_message(self, handler):
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',suggest:Não sei te dizer a data exata, '
            'mas posso te mandar um time aleatório! Use ,time',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            mentioned_jids=['bot_jid@s.whatsapp.net'],
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert len(result) == 1
        assert 'Não sei' in result[0].content.text
        assert 'time' in result[0].content.text

    @pytest.mark.anyio
    async def test_clarify_returns_question(self, handler):
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',clarify:Você quer ver a tabela de qual competição?',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            mentioned_jids=['bot_jid@s.whatsapp.net'],
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert len(result) == 1
        assert 'tabela' in result[0].content.text

    @pytest.mark.anyio
    async def test_clarify_empty_text_falls_back_to_menu_hint(self, handler):
        from bot.domain.constants import AGENT_MENU_HINT
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',clarify:',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == AGENT_MENU_HINT

    @pytest.mark.anyio
    async def test_clarify_whitespace_text_falls_back_to_menu_hint(self, handler):
        from bot.domain.constants import AGENT_MENU_HINT
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',clarify:   ',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == AGENT_MENU_HINT

    @pytest.mark.anyio
    async def test_suggest_empty_text_falls_back_to_menu_hint(self, handler):
        from bot.domain.constants import AGENT_MENU_HINT
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',suggest:',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == AGENT_MENU_HINT

    @pytest.mark.anyio
    async def test_suggest_whitespace_text_falls_back_to_menu_hint(self, handler):
        from bot.domain.constants import AGENT_MENU_HINT
        from bot.domain.models.command_data import CommandData

        data = CommandData(
            text=',suggest:   ',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            is_group=True,
        )

        result = await handler.handle(data)

        assert result is not None
        assert result[0].content.text == AGENT_MENU_HINT


class TestAgentOrchestratorSelection:
    @pytest.mark.anyio
    async def test_uses_configured_graph_orchestrator(self, handler, mocker):
        from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator

        data = GroupCommandDataFactory.build(text='@resenhazord algo')
        graph = mocker.Mock()
        graph.run = mocker.AsyncMock(return_value=data)
        mocker.patch.object(GraphAgentOrchestrator, 'configured', return_value=graph)

        await handler._run_agent(data)

        graph.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_falls_back_to_executor_without_graph(self, handler, mocker):
        from bot.infrastructure.llm.graph_orchestrator import GraphAgentOrchestrator
        from bot.infrastructure.llm.provider_chain import ProviderChain

        data = GroupCommandDataFactory.build(text='@resenhazord algo')
        mocker.patch.object(GraphAgentOrchestrator, 'configured', return_value=None)
        instance_spy = mocker.patch.object(
            ProviderChain, 'instance', side_effect=RuntimeError('not configured')
        )

        await handler._run_agent(data)

        instance_spy.assert_called_once()
