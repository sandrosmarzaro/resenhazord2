"""LLM Agent Executor - maps natural language to bot commands."""

from dataclasses import replace
from typing import ClassVar

import httpx
import structlog

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES, SYSTEM_PROMPT_TEMPLATE
from bot.domain.constants import (
    AGENT_MENU_HINT,
    CLARIFY_PREFIX,
    LLM_CLARIFY_MARKER,
    LLM_SUGGEST_MARKER,
    SUGGEST_PREFIX,
)
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    get_command_list_with_descriptions,
)
from bot.ports.example_retriever_port import ExampleRetrieverPort

logger = structlog.get_logger()


class AgentExecutor:
    MAX_AGENT_EXAMPLES: ClassVar[int] = 20
    MAX_USER_INPUT_LENGTH: ClassVar[int] = 2000
    MAX_CONTEXT_LENGTH: ClassVar[int] = 2000
    BOT_MENTION_TAG: ClassVar[str] = '@resenhazord'
    _AGENT_UNAVAILABLE_MSG: ClassVar[str] = f'🤖 IA indisponível no momento. {AGENT_MENU_HINT}'
    _AGENT_UNRESOLVABLE_MSG: ClassVar[str] = f'🤖 Não consegui entender. {AGENT_MENU_HINT}'

    def __init__(
        self,
        registry: CommandRegistry | None = None,
        retriever: ExampleRetrieverPort | None = None,
    ) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._retriever = retriever
        self._tools = build_tools_for_prompt(self._registry)
        self._command_list = get_command_list_with_descriptions(self._registry)
        self._translator = AgentResponseTranslator(self._registry)

    async def run(self, data: CommandData) -> CommandData:
        """Execute agent: map natural language to command.

        Returns CommandData with rewritten text for command execution.
        """
        examples = await self._select_examples(data.text)
        prompt = self._build_prompt(data.text, examples, context=data.quoted_text)

        logger.info('agent_executing', user_input=data.text, tool_count=len(self._tools))

        try:
            response = await ProviderChain.instance().complete(prompt, self._tools)
        except (httpx.HTTPError, RuntimeError) as e:
            logger.warning('agent_provider_failed', error=str(e))
            return self._fallback(data, self._AGENT_UNAVAILABLE_MSG)

        if response.tool_call:
            return self._translator.translate(
                data,
                response.tool_call.get('name', ''),
                response.tool_call.get('arguments', '{}'),
            )

        content = AgentResponseTranslator.normalize_flags(
            response.content.strip().strip('`').strip('"\'').strip()
        )

        if content.startswith((',', '/')):
            return self._translator.translate(data, content.lstrip(',/').strip('\'"'), '')

        if content.startswith(LLM_CLARIFY_MARKER):
            question = content[len(LLM_CLARIFY_MARKER) :].strip()
            if not question:
                return self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)
            logger.info('agent_asking_clarification', question=question)
            return replace(data, text=f'{CLARIFY_PREFIX}{question}')

        if content.startswith(LLM_SUGGEST_MARKER):
            suggestion = content[len(LLM_SUGGEST_MARKER) :].strip()
            if not suggestion:
                return self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)
            logger.info('agent_suggesting_command', suggestion=suggestion)
            return replace(data, text=f'{SUGGEST_PREFIX}{suggestion}')

        logger.warning('agent_no_tool_call', content=content, tool_call=response.tool_call)
        return self._fallback(data, self._AGENT_UNRESOLVABLE_MSG)

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
        self, user_input: str, examples: list[tuple[str, str]], context: str | None = None
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

        return SYSTEM_PROMPT_TEMPLATE.format(
            command_list=self._command_list,
            examples=examples_text,
            user_input=filtered_input,
            context=context_block,
            user_context=user_block,
        )

    def _fallback(self, data: CommandData, message: str) -> CommandData:
        return replace(data, text=f'{CLARIFY_PREFIX}{message}')
