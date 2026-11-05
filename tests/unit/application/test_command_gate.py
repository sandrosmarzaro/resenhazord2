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
