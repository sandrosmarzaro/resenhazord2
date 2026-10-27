from collections.abc import Iterable

import structlog

from bot.application.command_registry import CommandRegistry
from bot.domain.commands.base import Command
from bot.domain.models.agent_decision import AgentOutcome
from bot.domain.models.conversation import Conversation
from bot.infrastructure.metrics import record_agent_retrieval

logger = structlog.get_logger()


class AgentFeedback:
    """What users' answers say about the agent: the denials to learn from, and the
    retrieval recall@k over the commands they actually ran."""

    @staticmethod
    def denied(conversation: Conversation, reply: str) -> None:
        # One event holding the wrong mapping and its context: the raw material for
        # new retrieval examples and eval cases.
        logger.info(
            'agent_denied',
            request=conversation.request,
            proposed=conversation.proposed_command,
            reply=reply,
        )

    @staticmethod
    def executed(
        examples: list[tuple[str, str, float]], outcome: AgentOutcome, command: str
    ) -> None:
        # A direct match is the top example by definition, and the static fallback
        # (score 0) was never retrieved: neither says anything about recall.
        if outcome == AgentOutcome.DIRECT or any(score == 0 for *_, score in examples):
            return
        hit = AgentFeedback.recalls(
            [example_command for _, example_command, _ in examples], command
        )
        record_agent_retrieval(outcome, hit=hit)

    @staticmethod
    def recalls(example_commands: Iterable[str], command: str) -> bool:
        # Examples spell commands as users do (',score' for ',placar', ',pokemon' for
        # ',pokémon'), so both sides resolve through the same routing the bot uses.
        target = AgentFeedback._resolve(command)
        return target is not None and any(
            AgentFeedback._resolve(example) is target for example in example_commands
        )

    @staticmethod
    def _resolve(command: str) -> Command | None:
        return CommandRegistry.instance().get_strategy(command)
