import time
from collections.abc import Awaitable
from dataclasses import asdict, dataclass, replace
from typing import Any, ClassVar, Protocol, TypedDict, cast

import structlog
from langchain_core.runnables import RunnableConfig

from bot.application.agent_response import AgentResponseTranslator
from bot.application.example_selector import ExampleSelector
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.data.agent_replies import ASK_AGAIN_QUESTION
from bot.domain.constants import CLARIFY_PREFIX, SUGGEST_PREFIX
from bot.domain.models.agent_decision import AgentDecision, AgentOutcome
from bot.domain.models.command_data import CommandData
from bot.domain.models.conversation import Conversation
from bot.domain.models.conversation_status import ConversationStatus
from bot.domain.models.retrieved_example import RetrievedExample
from bot.infrastructure.metrics import record_agent_mapping

logger = structlog.get_logger()


class AgentTurnState(TypedDict, total=False):
    # Primitives only: the Redis checkpointer will refuse to deserialize custom types.
    conversation: dict[str, Any]
    intent: str
    examples: list[tuple[str, str, float]]
    decision: dict[str, str]
    result_text: str
    result_jid: str


class Node(Protocol):
    # Nodes that only read state are sync; LangGraph runs both kinds.
    def __call__(
        self, state: AgentTurnState, config: RunnableConfig
    ) -> dict[str, Any] | Awaitable[dict[str, Any]]: ...


@dataclass(frozen=True)
class _ReplySpec:
    prefix: str
    keeps_waiting: bool
    fixed: AgentDecision | None = None


class AgentGraphNodes:
    """LangGraph glue: each node loads the turn, delegates, and stores primitives back.
    The conversation rules live in Conversation; the edges in GraphAgentOrchestrator."""

    # A reply that keeps waiting stores its text as the pending question, plus the
    # decision's command when there is one (that makes it a yes/no confirmation).
    _REPLIES: ClassVar[dict[str, _ReplySpec]] = {
        'confirm': _ReplySpec(CLARIFY_PREFIX, keeps_waiting=True),
        'ask': _ReplySpec(CLARIFY_PREFIX, keeps_waiting=True),
        'ask_again': _ReplySpec(
            CLARIFY_PREFIX,
            keeps_waiting=True,
            fixed=AgentDecision(AgentOutcome.DENIED, text=ASK_AGAIN_QUESTION),
        ),
        'menu_hint': _ReplySpec(
            CLARIFY_PREFIX,
            keeps_waiting=False,
            fixed=AgentDecision(AgentOutcome.MENU_HINT, text=LLMCommandMapper.UNRESOLVABLE_MSG),
        ),
        'suggest': _ReplySpec(SUGGEST_PREFIX, keeps_waiting=False),
        'fallback': _ReplySpec(CLARIFY_PREFIX, keeps_waiting=False),
    }

    def __init__(
        self,
        selector: ExampleSelector,
        mapper: LLMCommandMapper,
        translator: AgentResponseTranslator,
    ) -> None:
        self._selector = selector
        self._mapper = mapper
        self._translator = translator

    def nodes(self) -> dict[str, Node]:
        replies = {name: self._reply_node(spec) for name, spec in self._REPLIES.items()}
        return {
            'route_input': self._route_input,
            'retrieve_examples': self._retrieve_examples,
            'call_llm': self._call_llm,
            'execute': self._execute,
            'execute_proposed': self._execute_proposed,
            **replies,
        }

    @staticmethod
    def conversation_of(state: AgentTurnState) -> Conversation:
        fields = dict(state.get('conversation') or {})
        status = ConversationStatus(fields.pop('status', ConversationStatus.IDLE))
        return Conversation(status=status, **fields)

    def _route_input(self, state: AgentTurnState, config: RunnableConfig) -> dict[str, Any]:
        conversation = self.conversation_of(state).resumed(time.time())
        return {
            'conversation': self._dump(conversation),
            'intent': str(conversation.intent(self._data(config).text)),
        }

    async def _retrieve_examples(
        self, state: AgentTurnState, config: RunnableConfig
    ) -> dict[str, Any]:
        data = self._with_context(state, config)
        examples = await self._selector.select(data.text)
        rows = [(example.text, example.command, example.score) for example in examples]
        direct = self._selector.direct_match(data, examples)
        if direct is None:
            return {'examples': rows, 'decision': {}}
        logger.info('agent_direct_match', example=direct.text, score=direct.score)
        decision = AgentDecision(AgentOutcome.DIRECT, command=direct.command)
        return {'examples': rows, 'decision': self._dump(decision)}

    async def _call_llm(self, state: AgentTurnState, config: RunnableConfig) -> dict[str, Any]:
        examples = [RetrievedExample(*row) for row in state.get('examples', [])]
        decision = await self._mapper.map(self._with_context(state, config), examples)
        return {'decision': self._dump(decision)}

    def _execute(self, state: AgentTurnState, config: RunnableConfig) -> dict[str, Any]:
        decision = self._decision(state)
        return self._finish(decision, self._run(config, decision.command), Conversation())

    def _execute_proposed(self, state: AgentTurnState, config: RunnableConfig) -> dict[str, Any]:
        command = self.conversation_of(state).proposed_command
        result = self._run(config, command)
        return self._finish(AgentDecision(AgentOutcome.CONFIRMED), result, Conversation())

    def _reply_node(self, spec: _ReplySpec) -> Node:
        def reply(state: AgentTurnState, config: RunnableConfig) -> dict[str, Any]:
            decision = spec.fixed or self._decision(state)
            conversation = Conversation()
            if spec.keeps_waiting:
                conversation = self.conversation_of(state).awaiting(
                    decision.text, time.time(), proposed_command=decision.command
                )
            result = replace(self._data(config), text=f'{spec.prefix}{decision.text}')
            return self._finish(decision, result, conversation)

        return reply

    def _run(self, config: RunnableConfig, command: str) -> CommandData:
        return self._translator.translate(self._data(config), command.lstrip(','), '')

    def _finish(
        self, decision: AgentDecision, result: CommandData, conversation: Conversation
    ) -> dict[str, Any]:
        record_agent_mapping(decision.outcome, decision.provider, decision.prompt_version)
        return {
            'result_text': result.text,
            'result_jid': result.jid,
            'conversation': self._dump(conversation),
        }

    @staticmethod
    def _dump(model: Conversation | AgentDecision) -> dict[str, Any]:
        # StrEnum members become plain str so the checkpoint holds primitives only.
        return {
            key: str(value) if isinstance(value, str) else value
            for key, value in asdict(model).items()
        }

    @staticmethod
    def _decision(state: AgentTurnState) -> AgentDecision:
        fields = state.get('decision') or {}
        return AgentDecision(
            AgentOutcome(fields['outcome']),
            command=fields.get('command', ''),
            text=fields.get('text', ''),
            provider=fields.get('provider', ''),
            prompt_version=fields.get('prompt_version', ''),
        )

    @staticmethod
    def _data(config: RunnableConfig) -> CommandData:
        # data rides the config (ephemeral, never checkpointed); only primitives persist.
        return cast('CommandData', (config.get('configurable') or {})['data'])

    def _with_context(self, state: AgentTurnState, config: RunnableConfig) -> CommandData:
        data = self._data(config)
        # Quote wins: a quoted message already carries the bot's question as context.
        question = self.conversation_of(state).question
        return replace(data, quoted_text=data.quoted_text or question or None)
