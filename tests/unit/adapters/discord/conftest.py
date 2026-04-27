import pytest

from bot.domain.commands.base import Command, CommandConfig


@pytest.fixture
def fake_command(mocker):
    def _build(config: CommandConfig, description: str = 'Test description'):
        cmd = mocker.MagicMock(spec=Command)
        cmd.config = config
        cmd.menu_description = description
        return cmd

    return _build


def patch_slash_registry(mocker, commands: list) -> None:
    mock_registry = mocker.patch('bot.adapters.discord.slash_register.CommandRegistry')
    mock_registry.instance.return_value.get_all.return_value = commands
