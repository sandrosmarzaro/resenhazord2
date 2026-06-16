from typing import Protocol

from bot.domain.models.command_data import CommandData


class AgentOrchestratorPort(Protocol):
    async def run(self, data: CommandData) -> CommandData: ...
