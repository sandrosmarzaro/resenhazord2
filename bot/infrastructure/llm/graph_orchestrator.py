from __future__ import annotations

import time
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph

from bot.application.agent_executor import AgentExecutor
from bot.domain.constants import CLARIFY_PREFIX, SUGGEST_PREFIX

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import BaseCheckpointSaver

    from bot.domain.models.command_data import CommandData
    from bot.ports.agent_orchestrator_port import AgentOrchestratorPort

logger = structlog.get_logger()


class _State(TypedDict):
    open_question: str
    asked_at: float
    result_text: str
    result_jid: str


class GraphAgentOrchestrator:
    DEFAULT_PLATFORM: ClassVar[str] = 'whatsapp'
    RESUME_WINDOW_SECONDS: ClassVar[float] = 90.0
    STORAGE_TTL_MINUTES: ClassVar[float] = 2.0

    _instance: ClassVar[GraphAgentOrchestrator | None] = None

    def __init__(
        self, executor: AgentOrchestratorPort | None = None, redis_url: str | None = None
    ) -> None:
        self._executor = executor or AgentExecutor()
        self._checkpointer = self._build_checkpointer(redis_url)
        self._needs_setup = isinstance(self._checkpointer, AsyncRedisSaver)
        self._graph = self._build_graph()

    @classmethod
    def configure(cls, redis_url: str | None = None) -> GraphAgentOrchestrator:
        cls._instance = cls(redis_url=redis_url)
        return cls._instance

    @classmethod
    def configured(cls) -> GraphAgentOrchestrator | None:
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    async def run(self, data: CommandData) -> CommandData:
        await self._ensure_setup()
        # data rides the config (ephemeral, never checkpointed); only primitives persist.
        config: RunnableConfig = {
            'configurable': {'thread_id': self._thread_id(data), 'data': data}
        }
        state = await self._graph.ainvoke(cast('_State', {}), config)
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

    def _build_graph(self):
        graph = StateGraph(_State)
        graph.add_node('turn', self._turn)
        graph.add_edge(START, 'turn')
        graph.add_edge('turn', END)
        return graph.compile(checkpointer=self._checkpointer)

    async def _turn(self, state: _State, config: RunnableConfig) -> _State:
        data = cast('CommandData', (config.get('configurable') or {})['data'])
        question = self._resumable_question(state, data)
        if question:
            data = replace(data, quoted_text=question)
        result = await self._executor.run(data)
        new_question = self._extract_question(result)
        return {
            'open_question': new_question,
            'asked_at': time.time() if new_question else 0.0,
            'result_text': result.text,
            'result_jid': result.jid,
        }

    def _resumable_question(self, state: _State, data: CommandData) -> str:
        # Quote wins: a quoted message already carries the bot's question as context.
        if data.quoted_text:
            return ''
        question = state.get('open_question', '')
        if not question:
            return ''
        within_window = time.time() - state.get('asked_at', 0.0) <= self.RESUME_WINDOW_SECONDS
        return question if within_window else ''

    @staticmethod
    def _extract_question(result: CommandData) -> str:
        for prefix in (CLARIFY_PREFIX, SUGGEST_PREFIX):
            if result.text.startswith(prefix):
                return result.text[len(prefix) :].strip()
        return ''

    @classmethod
    def _thread_id(cls, data: CommandData) -> str:
        platform = data.platform or cls.DEFAULT_PLATFORM
        user = data.participant or data.sender_jid
        return f'{platform}:{data.jid}:{user}'
