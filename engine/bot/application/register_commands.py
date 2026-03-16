"""Register all Python-side commands with the CommandRegistry."""

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.d20 import D20Command
from bot.domain.commands.fato import FatoCommand
from bot.domain.commands.mateus import MateusCommand
from bot.domain.commands.oi import OiCommand


def register_all_commands() -> None:
    registry = CommandRegistry.instance()
    registry.register(D20Command())
    registry.register(FatoCommand())
    registry.register(MateusCommand())
    registry.register(OiCommand())
