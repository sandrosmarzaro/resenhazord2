import pytest

from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command, CommandConfig, CommandScope, ParsedCommand
from bot.domain.constants import AGENT_MENU_HINT
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.domain.models.contents.text_content import TextContent
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
def agent(mocker):
    agent = mocker.Mock()
    agent.run = mocker.AsyncMock()
    return agent


@pytest.fixture
def handler(registry, agent, mock_dev_list, mock_config_service):
    return CommandHandler(
        registry=registry, agent=agent, dev_list=mock_dev_list, config_service=mock_config_service
    )


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


class TestPerGroupConfig:
    @pytest.mark.anyio
    async def test_command_off_in_chat_returns_off_message(
        self, registry, agent, mock_dev_list, mocker
    ):
        config_service = mocker.AsyncMock()
        config_service.is_enabled.return_value = False
        handler = CommandHandler(
            registry=registry, agent=agent, dev_list=mock_dev_list, config_service=config_service
        )
        data = GroupCommandDataFactory.build(text=', pub')

        result = await handler.handle(data)

        assert result is not None
        content = result[0].content
        assert isinstance(content, TextContent)
        assert 'neste chat' in content.text

    @pytest.mark.anyio
    async def test_consults_config_with_command_config(self, handler, mock_config_service):
        data = GroupCommandDataFactory.build(text=', pub')

        await handler.handle(data)

        mock_config_service.is_enabled.assert_awaited_once()
        assert mock_config_service.is_enabled.await_args.args[1].name == 'pub'

    @pytest.mark.anyio
    async def test_disabled_scope_skips_per_group_check(self, handler, mock_config_service):
        data = GroupCommandDataFactory.build(text=', off')

        await handler.handle(data)

        mock_config_service.is_enabled.assert_not_called()


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
    async def test_agent_trigger_in_dm(self, handler, agent):
        agent.run.return_value = None
        data = _dm('me mande um yugioh')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_agent_trigger_with_send_me_pattern(self, handler, agent):
        agent.run.return_value = None
        data = _group('me mande um pacotinho de yugioh')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_no_agent_for_plain_command_in_group(self, handler, agent):
        data = GroupCommandDataFactory.build(text=',pub')

        await handler.handle(data)

        agent.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_no_agent_for_direct_command_in_dm(self, handler, agent):
        data = _dm(',pub')

        await handler.handle(data)

        agent.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_agent_for_unmatched_command_in_dm(self, handler, agent):
        agent.run.return_value = None
        data = _dm(',unknown')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_agent_for_natural_language_in_dm(self, handler, agent):
        agent.run.return_value = None
        data = _dm('qual o placar do jogo?')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_no_agent_for_natural_language_in_group(self, handler, agent):
        data = _group('qual o placar do jogo?')

        await handler.handle(data)

        agent.run.assert_not_awaited()

    @pytest.mark.anyio
    async def test_agent_trigger_by_bot_mention_tag(self, handler, agent):
        agent.run.return_value = None
        data = _group('@resenhazord ver placar')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_agent_trigger_by_mentioned_jid(
        self, registry, agent, mock_dev_list, mock_config_service, mocker
    ):
        mocker.patch(
            'bot.application.command_handler.Settings',
            return_value=mocker.MagicMock(
                resenhazord2_jid='555@s.whatsapp.net',
                resenha_jid='',
                resenhazord2_lid='',
            ),
        )
        handler = CommandHandler(
            registry=registry,
            agent=agent,
            dev_list=mock_dev_list,
            config_service=mock_config_service,
        )
        agent.run.return_value = None
        data = CommandData(
            text='hello',
            jid='test@g.us',
            sender_jid='test@s.whatsapp.net',
            mentioned_jids=['555@s.whatsapp.net'],
            is_group=True,
        )

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)


class TestHandleRouting:
    @pytest.mark.anyio
    async def test_dm_natural_language_routed_through_agent_then_dispatched(self, handler, agent):
        data = _dm('manda um negócio público')
        agent.run.return_value = _dm(',pub')

        result = await handler.handle(data)

        agent.run.assert_awaited_once_with(data)
        assert result[0].content.text == 'public ok'

    @pytest.mark.anyio
    async def test_dm_direct_command_skips_agent(self, handler, agent):
        result = await handler.handle(_dm(',pub'))

        agent.run.assert_not_awaited()
        assert result[0].content.text == 'public ok'


class TestOnMatch:
    @pytest.mark.anyio
    async def test_hands_the_matched_command_to_the_hook(self, handler, registry, mocker):
        on_match = mocker.AsyncMock()
        data = GroupCommandDataFactory.build(text=',pub')

        await handler.handle(data, on_match=on_match)

        on_match.assert_awaited_once_with(registry.get_strategy(',pub'))

    @pytest.mark.anyio
    async def test_skips_the_hook_for_a_rejected_command(self, handler, mocker):
        on_match = mocker.AsyncMock()
        data = GroupCommandDataFactory.build(text=',off')

        await handler.handle(data, on_match=on_match)

        on_match.assert_not_awaited()


class TestAgentDeclined:
    @pytest.mark.anyio
    async def test_declined_agent_turn_gets_no_reply(self, handler, agent):
        agent.run.return_value = None

        result = await handler.handle(_dm('Entendi o que você precisa'))

        assert result is None


def _dm(text: str) -> CommandData:
    return CommandData(
        text=text, jid='user@s.whatsapp.net', sender_jid='user@s.whatsapp.net', is_group=False
    )


def _group(text: str) -> CommandData:
    return CommandData(text=text, jid='test@g.us', sender_jid='test@s.whatsapp.net', is_group=True)


class FailingCommand(Command):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._error = error

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='falha')

    @property
    def menu_description(self) -> str:
        return ''

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        raise self._error


class TestRunAgent:
    @pytest.mark.anyio
    async def test_runs_the_command_the_agent_mapped_to(self, handler, agent):
        agent.run.return_value = _group(',pub')

        result = await handler.handle(_group('@resenhazord manda o público'))

        assert result[0].content.text == 'public ok'

    @pytest.mark.anyio
    async def test_invalid_agent_response_replies_the_clarify_fallback(self, handler, agent):
        agent.run.side_effect = ValueError('invalid response')

        result = await handler.handle(_group('@resenhazord ver placar'))

        assert result[0].content.text == f'Erro inesperado. {AGENT_MENU_HINT}'


class TestRunCommand:
    @pytest.mark.anyio
    async def test_bot_error_reraises(self, handler, registry):
        registry.register(FailingCommand(BotError('custom')))
        data = _group(',falha')

        with pytest.raises(BotError, match='custom'):
            await handler.handle(data)

    @pytest.mark.anyio
    async def test_generic_exception_reraises(self, handler, registry):
        registry.register(FailingCommand(RuntimeError('boom')))
        data = _group(',falha')

        with pytest.raises(RuntimeError, match='boom'):
            await handler.handle(data)


class TestProcessingOrder:
    @pytest.mark.anyio
    async def test_agent_sees_the_text_before_the_batch_suffix_is_parsed(self, handler, agent):
        agent.run.return_value = None
        data = _dm('me mande um pub 2x')

        await handler.handle(data)

        agent.run.assert_awaited_once_with(data)

    @pytest.mark.anyio
    async def test_batch_suffix_of_the_mapped_command_applies(self, handler, agent, mock_dev_list):
        mock_dev_list.is_dev.return_value = True
        agent.run.return_value = _dm(',pub 3x')

        result = await handler.handle(_dm('manda três públicos'))

        assert len(result) == 3

    @pytest.mark.anyio
    async def test_batch_suffix_is_stripped_before_a_clarify_reply(self, handler):
        result = await handler.handle(_group(',clarify:Quer quantos? 3x'))

        assert result[0].content.text == 'Quer quantos?'


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
