from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast

import structlog
from langgraph.checkpoint.memory import MemorySaver
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


class GraphAgentOrchestrator:
    DEFAULT_PLATFORM: ClassVar[str] = 'whatsapp'

    def __init__(self, executor: AgentExecutor | None = None) -> None:
        self._executor = executor or AgentExecutor()
        self._graph = self._build_graph()

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
        return graph.compile(checkpointer=MemorySaver())

    async def _turn(self, state: _State) -> _State:
        data = state['data']
        open_question = state.get('open_question', '')
        if open_question:
            data = replace(data, quoted_text=open_question)
        result = await self._executor.run(data)
        return {'data': data, 'result': result, 'open_question': self._extract_question(result)}

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
