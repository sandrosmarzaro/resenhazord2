import pytest

from bot.application.command_gate import CommandGate
from bot.domain.commands.base import Command, CommandConfig, CommandScope, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from tests.factories.command_data import GroupCommandDataFactory


class _Scoped(Command):
    def __init__(self, scope: CommandScope) -> None:
        super().__init__()
        self._scope = scope

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(name='porno', scope=self._scope)

    @property
    def menu_description(self) -> str:
        return 'Escopo.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        return []


@pytest.fixture
def rejections(mocker):
    return mocker.patch('bot.infrastructure.metrics._rejections')


@pytest.fixture
def gate(mock_dev_list, mock_config_service):
    return CommandGate(mock_dev_list, mock_config_service)


def _counted(rejections, reason: str, scope: CommandScope) -> None:
    rejections.add.assert_called_once_with(
        1, {'reason': reason, 'command.name': 'porno', 'command.scope': scope}
    )


class TestRejectionCounts:
    @pytest.mark.anyio
    async def test_counts_a_disabled_command(self, gate, rejections):
        await gate.rejection_text(_Scoped(CommandScope.DISABLED), GroupCommandDataFactory())

        _counted(rejections, 'disabled', CommandScope.DISABLED)

    @pytest.mark.anyio
    async def test_counts_a_dev_command_from_a_non_dev(self, gate, rejections):
        await gate.rejection_text(_Scoped(CommandScope.DEV), GroupCommandDataFactory())

        _counted(rejections, 'dev_only', CommandScope.DEV)

    @pytest.mark.anyio
    async def test_counts_a_command_the_chat_turned_off(
        self, gate, rejections, mock_config_service
    ):
        mock_config_service.is_enabled.return_value = False

        await gate.admit(_Scoped(CommandScope.NSFW), GroupCommandDataFactory(), 1)

        _counted(rejections, 'off_here', CommandScope.NSFW)

    @pytest.mark.anyio
    async def test_an_admitted_command_counts_nothing(self, gate, rejections):
        await gate.admit(_Scoped(CommandScope.NSFW), GroupCommandDataFactory(), 1)

        rejections.add.assert_not_called()


class TestBlockedSender:
    @pytest.mark.anyio
    async def test_admit_stays_silent_and_counts_it(self, gate, rejections, mock_config_service):
        mock_config_service.is_blocked.return_value = True

        rejection, _ = await gate.admit(_Scoped(CommandScope.PUBLIC), GroupCommandDataFactory(), 1)

        assert rejection == []
        _counted(rejections, 'blocked', CommandScope.PUBLIC)

    @pytest.mark.anyio
    async def test_rejection_text_is_empty(self, gate, mock_config_service):
        mock_config_service.is_blocked.return_value = True

        text = await gate.rejection_text(_Scoped(CommandScope.PUBLIC), GroupCommandDataFactory())

        assert text == ''

    @pytest.mark.anyio
    async def test_a_dev_is_exempt(self, gate, mock_config_service, mock_dev_list):
        mock_config_service.is_blocked.return_value = True
        mock_dev_list.is_dev.return_value = True
        data = GroupCommandDataFactory(platform='whatsapp')

        rejection, _ = await gate.admit(_Scoped(CommandScope.PUBLIC), data, 1)

        assert rejection is None
        mock_dev_list.is_dev.assert_awaited_once_with(data.sender_jid)


class TestBlocksAgent:
    @pytest.mark.anyio
    async def test_a_blocked_sender_is_turned_away_and_counted(
        self, gate, rejections, mock_config_service
    ):
        mock_config_service.is_blocked.return_value = True

        blocked = await gate.blocks_agent(GroupCommandDataFactory())

        assert blocked is True
        rejections.add.assert_called_once_with(
            1, {'reason': 'blocked', 'command.name': 'agent', 'command.scope': 'agent'}
        )

    @pytest.mark.anyio
    async def test_an_unblocked_sender_passes_uncounted(self, gate, rejections):
        blocked = await gate.blocks_agent(GroupCommandDataFactory())

        assert blocked is False
        rejections.add.assert_not_called()

    @pytest.mark.anyio
    async def test_a_blocked_dev_passes(self, gate, mock_config_service, mock_dev_list):
        mock_config_service.is_blocked.return_value = True
        mock_dev_list.is_dev.return_value = True

        assert await gate.blocks_agent(GroupCommandDataFactory()) is False
