from typing import Protocol

from bot.domain.models.system_prompt import SystemPrompt


class PromptRegistryError(Exception):
    pass


class PromptRegistryPort(Protocol):
    def system_prompt(self) -> SystemPrompt: ...
