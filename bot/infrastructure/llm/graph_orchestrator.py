from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, cast

import structlog
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph
from redis.exceptions import RedisError

from bot.domain.models.agent_decision import AgentOutcome
from bot.domain.models.conversation import TurnIntent
from bot.infrastructure.llm.agent_graph_nodes import AgentGraphNodes, AgentTurnState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph

    from bot.domain.models.command_data import CommandData

logger = structlog.get_logger()


class GraphAgentOrchestrator:
    """Conversation state machine: each message enters at START and route_input reads
    whether the chat is idle, waiting for a confirmation or waiting for an answer."""

    DEFAULT_PLATFORM: ClassVar[str] = 'whatsapp'
    STORAGE_TTL_MINUTES: ClassVar[float] = 5.0
    _AFTER_INPUT: ClassVar[dict[str, str]] = {
        TurnIntent.CONFIRMED: 'execute_proposed',
        TurnIntent.DENIED: 'ask_again',
        TurnIntent.REQUEST: 'retrieve_examples',
    }
    _AFTER_LLM: ClassVar[dict[str, str]] = {
        AgentOutcome.COMMAND: 'execute',
        AgentOutcome.CONFIRM: 'confirm',
        AgentOutcome.CLARIFY: 'ask',
        AgentOutcome.SUGGEST: 'suggest',
        AgentOutcome.UNRESOLVABLE: 'fallback',
        AgentOutcome.UNAVAILABLE: 'fallback',
    }
    _TERMINALS: ClassVar[tuple[str, ...]] = (
        'execute',
        'execute_proposed',
        'confirm',
        'ask',
        'ask_again',
        'menu_hint',
        'suggest',
        'fallback',
    )

    def __init__(self, nodes: AgentGraphNodes, redis_url: str | None = None) -> None:
        self._nodes = nodes
        checkpointer = self._build_checkpointer(redis_url)
        self._needs_setup = isinstance(checkpointer, AsyncRedisSaver)
        self._checkpointer = checkpointer
        self._graph = self._build_graph(checkpointer)

    async def run(self, data: CommandData) -> CommandData:
        try:
            await self._ensure_setup()
            return await self._invoke(self._graph, data)
        except RedisError as error:
            # Lost conversation memory beats a silent bot: answer this turn statelessly.
            logger.warning('agent_checkpointer_unavailable', error=str(error))
            return await self._invoke(self._build_graph(MemorySaver()), data)

    async def _invoke(self, graph: CompiledStateGraph, data: CommandData) -> CommandData:
        config: RunnableConfig = {
            'configurable': {'thread_id': self._thread_id(data), 'data': data}
        }
        state = await graph.ainvoke(cast('AgentTurnState', {}), config)
        return replace(data, text=state['result_text'], jid=state['result_jid'])

    async def _ensure_setup(self) -> None:
        if not self._needs_setup:
            return
        await cast('AsyncRedisSaver', self._checkpointer).asetup()
        self._needs_setup = False

    def _build_checkpointer(self, redis_url: str | None) -> BaseCheckpointSaver:
        if not redis_url:
            return MemorySaver()
        ttl = {'default_ttl': self.STORAGE_TTL_MINUTES, 'refresh_on_read': False}
        return AsyncRedisSaver(redis_url, ttl=ttl)

    def _build_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        graph: StateGraph = StateGraph(AgentTurnState)
        for name, node in self._nodes.nodes().items():
            graph.add_node(name, node)
        graph.add_edge(START, 'route_input')
        graph.add_conditional_edges(
            'route_input', self._after_input, list(set(self._AFTER_INPUT.values()))
        )
        graph.add_conditional_edges(
            'retrieve_examples', self._after_retrieval, ['execute', 'call_llm']
        )
        graph.add_conditional_edges(
            'call_llm', self._after_llm, [*set(self._AFTER_LLM.values()), 'menu_hint']
        )
        for terminal in self._TERMINALS:
            graph.add_edge(terminal, END)
        return graph.compile(checkpointer=checkpointer)

    @classmethod
    def _after_input(cls, state: AgentTurnState) -> str:
        return cls._AFTER_INPUT[state.get('intent', TurnIntent.REQUEST)]

    @staticmethod
    def _after_retrieval(state: AgentTurnState) -> str:
        # A direct match already filled the decision; otherwise the LLM decides.
        return 'execute' if state.get('decision') else 'call_llm'

    @classmethod
    def _after_llm(cls, state: AgentTurnState) -> str:
        outcome = state.get('decision', {}).get('outcome', AgentOutcome.UNRESOLVABLE)
        if outcome == AgentOutcome.CLARIFY and AgentGraphNodes.conversation_of(state).exhausted:
            return 'menu_hint'
        return cls._AFTER_LLM[outcome]

    @classmethod
    def _thread_id(cls, data: CommandData) -> str:
        platform = data.platform or cls.DEFAULT_PLATFORM
        user = data.participant or data.sender_jid
        return f'{platform}:{data.jid}:{user}'
