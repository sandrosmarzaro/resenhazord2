from bot.domain.commands.base import Command


class CommandRegistry:
    _instance: 'CommandRegistry | None' = None

    def __init__(self) -> None:
        self._commands: list[Command] = []

    @classmethod
    def instance(cls) -> 'CommandRegistry':
        if cls._instance is None:
            cls._instance = CommandRegistry()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def register(self, command: Command) -> None:
        self._commands.append(command)

    def get_strategy(self, text: str) -> Command | None:
        for cmd in self._commands:
            if cmd.matches(text):
                return cmd
        return None

    def get_all(self) -> list[Command]:
        return list(self._commands)
