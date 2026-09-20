from dataclasses import dataclass


@dataclass(frozen=True)
class SystemPrompt:
    template: str
    version: str
