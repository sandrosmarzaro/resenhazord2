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
    OVER_BUDGET = 'over_budget'
    # Outcomes the conversation graph adds on a reply to the bot's own question.
    CONFIRMED = 'confirmed'
    DENIED = 'denied'
    MENU_HINT = 'menu_hint'


@dataclass(frozen=True)
class AgentDecision:
    outcome: AgentOutcome
    command: str = ''
    text: str = ''
    provider: str = ''
    prompt_version: str = ''
