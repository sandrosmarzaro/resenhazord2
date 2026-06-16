import time
from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from bot.application.agent_executor import AgentExecutor
from bot.domain.constants import CLARIFY_PREFIX, SUGGEST_PREFIX
from bot.domain.models.command_data import CommandData

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig

logger = structlog.get_logger()


class _State(TypedDict):
    data: CommandData
    result: CommandData
    open_question: str
    asked_at: float


class GraphAgentOrchestrator:
    DEFAULT_PLATFORM: ClassVar[str] = 'whatsapp'
    RESUME_WINDOW_SECONDS: ClassVar[float] = 90.0

    _instance: ClassVar['GraphAgentOrchestrator | None'] = None

    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self._executor = executor or AgentExecutor()
        self._graph = self._build_graph()

    @classmethod
    def configure(cls) -> 'GraphAgentOrchestrator':
        cls._instance = cls()
        return cls._instance

    @classmethod
    def configured(cls) -> 'GraphAgentOrchestrator | None':
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    async def run(self, data: CommandData) -> CommandData:
        config: RunnableConfig = {'configurable': {'thread_id': self._thread_id(data)}}
        # First-turn input carries only data; the checkpointer fills result/open_question.
        state = await self._graph.ainvoke(cast('_State', {'data': data}), config)
        return state['result']

    def _build_graph(self):
        graph = StateGraph(_State)
        graph.add_node('turn', self._turn)
        graph.add_edge(START, 'turn')
        graph.add_edge('turn', END)
        serde = JsonPlusSerializer(
            allowed_msgpack_modules=[('bot.domain.models.command_data', 'CommandData')]
        )
        return graph.compile(checkpointer=MemorySaver(serde=serde))

    async def _turn(self, state: _State) -> _State:
        data = state['data']
        question = self._resumable_question(state, data)
        if question:
            data = replace(data, quoted_text=question)
        result = await self._executor.run(data)
        new_question = self._extract_question(result)
        return {
            'data': data,
            'result': result,
            'open_question': new_question,
            'asked_at': time.time() if new_question else 0.0,
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
