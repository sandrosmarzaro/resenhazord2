"""LLM Agent Executor - maps natural language to bot commands."""

from dataclasses import replace

import structlog

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.application.example_selector import ExampleSelector
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.domain.constants import CLARIFY_PREFIX, SUGGEST_PREFIX
from bot.domain.models.agent_decision import AgentDecision, AgentOutcome
from bot.domain.models.command_data import CommandData
from bot.infrastructure.metrics import record_agent_mapping
from bot.ports.example_retriever_port import ExampleRetrieverPort
from bot.ports.llm_provider_port import LLMProviderPort
from bot.ports.prompt_registry_port import PromptRegistryPort

logger = structlog.get_logger()


class AgentExecutor:
    def __init__(
        self,
        registry: CommandRegistry,
        provider: LLMProviderPort,
        retriever: ExampleRetrieverPort | None = None,
        prompt_registry: PromptRegistryPort | None = None,
    ) -> None:
        self._selector = ExampleSelector(retriever)
        self._mapper = LLMCommandMapper(registry, provider, prompt_registry)
        self._translator = AgentResponseTranslator(registry)

    async def run(self, data: CommandData) -> CommandData:
        examples = await self._selector.select(data.text)
        if direct := self._selector.direct_match(data, examples):
            logger.info('agent_direct_match', example=direct.text, score=direct.score)
            decision = AgentDecision(AgentOutcome.DIRECT, command=direct.command)
        else:
            decision = await self._mapper.map(data, examples)
        record_agent_mapping(decision.outcome, decision.provider, decision.prompt_version)
        return self._render(data, decision)

    def _render(self, data: CommandData, decision: AgentDecision) -> CommandData:
        if decision.outcome in (AgentOutcome.COMMAND, AgentOutcome.DIRECT):
            return self._translator.translate(data, decision.command.lstrip(','), '')
        if decision.outcome == AgentOutcome.SUGGEST:
            return replace(data, text=f'{SUGGEST_PREFIX}{decision.text}')
        return replace(data, text=f'{CLARIFY_PREFIX}{decision.text}')
