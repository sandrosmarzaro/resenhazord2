from typing import Protocol


class PromptRegistryPort(Protocol):
    def system_prompt_template(self) -> str: ...
