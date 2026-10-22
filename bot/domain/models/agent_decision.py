from dataclasses import dataclass
from enum import StrEnum


class AgentOutcome(StrEnum):
    COMMAND = 'command'
    DIRECT = 'direct'
    CONFIRM = 'confirm'
    CLARIFY = 'clarify'
    SUGGEST = 'suggest'
    UNRESOLVABLE = 'unresolvable'
    UNAVAILABLE = 'unavailable'


@dataclass(frozen=True)
class AgentDecision:
    outcome: AgentOutcome
    command: str = ''
    text: str = ''
    provider: str = ''
    prompt_version: str = ''
