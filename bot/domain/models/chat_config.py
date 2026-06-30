from dataclasses import dataclass, field
from enum import StrEnum


class ChatType(StrEnum):
    GROUP = 'group'
    PRIVATE = 'private'


class ChatPolicy(StrEnum):
    OPEN = 'open'
    CURATED = 'curated'


@dataclass(frozen=True)
class ChatKey:
    platform: str
    native_id: str
    type: ChatType


@dataclass(frozen=True)
class ChatConfig:
    policy: ChatPolicy = ChatPolicy.OPEN
    overrides: dict[str, bool] = field(default_factory=dict)

    def override_for(self, command_name: str) -> bool | None:
        return self.overrides.get(command_name)
