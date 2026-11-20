from dataclasses import dataclass, field
from enum import StrEnum

from bot.domain.models.blocked_member import BlockedMember


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
    dev_admin: bool = False
    blocked: tuple[BlockedMember, ...] = ()

    def override_for(self, command_name: str) -> bool | None:
        return self.overrides.get(command_name)

    def blocks(self, member: BlockedMember) -> bool:
        return any(not member.keys.isdisjoint(blocked.keys) for blocked in self.blocked)
