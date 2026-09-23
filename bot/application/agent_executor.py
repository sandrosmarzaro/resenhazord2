"""LLM Agent Executor - maps natural language to bot commands."""

import json
from dataclasses import replace
from typing import ClassVar

import httpx
import structlog

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES, SYSTEM_PROMPT_TEMPLATE
from bot.data.agent_meta_tools import (
    AGENT_META_TOOLS,
    CLARIFY_TOOL_NAME,
    CONFIDENCE_ARG,
    CONFIDENCE_PROPERTY,
    SUGGEST_TOOL_NAME,
)
from bot.domain.constants import (
    AGENT_MENU_HINT,
    CLARIFY_PREFIX,
    SUGGEST_PREFIX,
)
from bot.domain.models.command_data import CommandData
from bot.domain.models.system_prompt import SystemPrompt
from bot.infrastructure.llm.langchain_provider import LangChainProvider
from bot.infrastructure.llm.langsmith_prompt_registry import (
    LangSmithPromptRegistry,
    PromptRegistryError,
)
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.providers.base import LLMResponse
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    get_command_list_with_descriptions,
)
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.infrastructure.metrics import record_agent_mapping
from bot.ports.example_retriever_port import ExampleRetrieverPort
from bot.ports.llm_provider_port import LLMProviderPort
from bot.ports.prompt_registry_port import PromptRegistryPort

logger = structlog.get_logger()


class AgentExecutor:
    MAX_AGENT_EXAMPLES: ClassVar[int] = 20
    CONFIDENCE_THRESHOLD: ClassVar[float] = 0.7
    MAX_USER_INPUT_LENGTH: ClassVar[int] = 2000
    MAX_CONTEXT_LENGTH: ClassVar[int] = 2000
    BOT_MENTION_TAG: ClassVar[str] = '@resenhazord'
    _AGENT_UNAVAILABLE_MSG: ClassVar[str] = f'🤖 IA indisponível no momento. {AGENT_MENU_HINT}'
    _AGENT_UNRESOLVABLE_MSG: ClassVar[str] = f'🤖 Não consegui entender. {AGENT_MENU_HINT}'

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        retriever: ExampleRetrieverPort | None = None,
        provider: LLMProviderPort | None = None,
        prompt_registry: PromptRegistryPort | None = None,
    ) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._retriever = retriever or UpstashExampleRetriever.configured()
        self._provider = provider or LangChainProvider.configured()
        self._prompt_registry = prompt_registry or LangSmithPromptRegistry.configured()
        command_tools = self._with_confidence(build_tools_for_prompt(self._registry))
        self._tools = command_tools + AGENT_META_TOOLS
        self._command_list = get_command_list_with_descriptions(self._registry)
        self._translator = AgentResponseTranslator(self._registry)

    async def run(self, data: CommandData) -> CommandData:
        """Execute agent: map natural language to command.

        Returns CommandData with rewritten text for command execution.
        """
        examples = await self._select_examples(data.text)

        logger.info('agent_executing', user_input=data.text, tool_count=len(self._tools))

        version = ''
        try:
            system_prompt = self._system_prompt()
            version = system_prompt.version
            prompt = self._build_prompt(
                system_prompt.template, data.text, examples, data.quoted_text
            )
            provider = self._provider or ProviderChain.instance()
            response = await provider.complete(prompt, self._tools)
        except (httpx.HTTPError, RuntimeError, PromptRegistryError) as e:
            logger.warning('agent_provider_failed', error=str(e))
            fallback = self._fallback(data, self._AGENT_UNAVAILABLE_MSG)
            return self._record(fallback, 'unavailable', '', version)

        outcome, result = self._interpret(data, response)
        return self._record(result, outcome, response.provider, version)

    def _system_prompt(self) -> SystemPrompt:
        if self._prompt_registry:
            return self._prompt_registry.system_prompt()
        return SystemPrompt(template=SYSTEM_PROMPT_TEMPLATE, version='')

    @staticmethod
    def _record(result: CommandData, outcome: str, provider: str, version: str) -> CommandData:
        record_agent_mapping(outcome, provider, version)
        return result

    def _interpret(self, data: CommandData, response: LLMResponse) -> tuple[str, CommandData]:
        if response.tool_call:
            return self._route_tool_call(data, response.tool_call)

        content = AgentResponseTranslator.normalize_flags(
            response.content.strip().strip('`').strip('"\'').strip()
        )
        if content.startswith((',', '/')):
            return 'command', self._translator.translate(
                data, content.lstrip(',/').strip('\'"'), ''
            )

        logger.warning('agent_no_tool_call', content=content, tool_call=response.tool_call)
        return 'unresolvable', self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)

    def _route_tool_call(self, data: CommandData, tool_call: dict) -> tuple[str, CommandData]:
        name = tool_call.get('name', '')
        arguments = tool_call.get('arguments', '{}')
        if name == CLARIFY_TOOL_NAME:
            return 'clarify', self._clarify(data, self._tool_arg(arguments, 'question'))
        if name == SUGGEST_TOOL_NAME:
            return 'suggest', self._suggest(data, self._tool_arg(arguments, 'message'))
        if self._confidence(arguments) < self.CONFIDENCE_THRESHOLD:
            return 'confirm', self._confirm(data, name, arguments)
        return 'command', self._translator.translate(data, name, arguments)

    def _confirm(self, data: CommandData, name: str, arguments: str) -> CommandData:
        command = self._translator.compose(name, arguments)
        proposed = AgentResponseTranslator.normalize_flags(command)
        logger.info('agent_confirming', proposed=proposed, original=data.text)
        return replace(data, text=f'{CLARIFY_PREFIX}Você quis dizer `{proposed}`?')

    @staticmethod
    def _confidence(arguments: str) -> float:
        try:
            return float(json.loads(arguments).get(CONFIDENCE_ARG, 1.0))
        except TypeError, ValueError:  # JSONDecodeError is a ValueError subclass
            return 1.0

    @staticmethod
    def _with_confidence(tools: list[dict]) -> list[dict]:
        for tool in tools:
            tool['function']['parameters']['properties'][CONFIDENCE_ARG] = CONFIDENCE_PROPERTY
        return tools

    def _clarify(self, data: CommandData, question: str) -> CommandData:
        if not question:
            return self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)
        logger.info('agent_asking_clarification', question=question)
        return replace(data, text=f'{CLARIFY_PREFIX}{question}')

    def _suggest(self, data: CommandData, message: str) -> CommandData:
        if not message:
            return self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)
        logger.info('agent_suggesting_command', suggestion=message)
        return replace(data, text=f'{SUGGEST_PREFIX}{message}')

    @staticmethod
    def _tool_arg(arguments: str, key: str) -> str:
        try:
            return str(json.loads(arguments).get(key, '')).strip()
        except json.JSONDecodeError:
            return ''

    async def _select_examples(self, user_input: str) -> list[tuple[str, str]]:
        if self._retriever is None:
            return list(AGENT_EXAMPLES[: self.MAX_AGENT_EXAMPLES])

        query = self._strip_mention(user_input)
        try:
            retrieved = await self._retriever.retrieve(query, self.MAX_AGENT_EXAMPLES)
        except httpx.HTTPError as error:
            logger.warning('agent_retrieval_failed', error=str(error))
            return list(AGENT_EXAMPLES[: self.MAX_AGENT_EXAMPLES])
        return [(example.text, example.command) for example in retrieved]

    @classmethod
    def _strip_mention(cls, text: str) -> str:
        return text.replace(cls.BOT_MENTION_TAG, '').strip()[: cls.MAX_USER_INPUT_LENGTH]

    def _build_prompt(
        self,
        template: str,
        user_input: str,
        examples: list[tuple[str, str]],
        context: str | None = None,
    ) -> str:
        filtered_input = self._strip_mention(user_input)
        truncated_context = context[: self.MAX_CONTEXT_LENGTH] if context else None

        examples_text = '\n'.join(
            f'Usuário: "{example}" -> Comando: {command}' for example, command in examples
        )

        if truncated_context:
            context_block = f'\nContexto da mensagem anterior: "{truncated_context}"'
            user_block = f'\nPedido do usuário (respondendo acima): {filtered_input}'
        else:
            context_block = ''
            user_block = f'\nPedido do usuário: {filtered_input}'

        return template.format(
            command_list=self._command_list,
            examples=examples_text,
            user_input=filtered_input,
            context=context_block,
            user_context=user_block,
        )

    def _fallback(self, data: CommandData, message: str) -> CommandData:
        return replace(data, text=f'{CLARIFY_PREFIX}{message}')
