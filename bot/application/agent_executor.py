"""LLM Agent Executor - maps natural language to bot commands."""

from dataclasses import replace
from typing import ClassVar

import httpx
import structlog

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES, SYSTEM_PROMPT_TEMPLATE
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import ProviderChain
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    get_command_list_with_descriptions,
)

logger = structlog.get_logger()


class AgentExecutor:
    MAX_AGENT_EXAMPLES: ClassVar[int] = 20
    MAX_USER_INPUT_LENGTH: ClassVar[int] = 2000
    MAX_CONTEXT_LENGTH: ClassVar[int] = 2000
    BOT_MENTION_TAG: ClassVar[str] = '@resenhazord'

    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self._registry = registry or CommandRegistry.instance()
        self._tools = build_tools_for_prompt(self._registry)
        self._command_list = get_command_list_with_descriptions(self._registry)
        self._translator = AgentResponseTranslator(self._registry)

    async def run(self, data: CommandData) -> CommandData:
        """Execute agent: map natural language to command.

        Returns CommandData with rewritten text for command execution.
        """
        prompt = self._build_prompt(data.text, context=data.quoted_text)

        logger.info('agent_executing', user_input=data.text, tool_count=len(self._tools))

        try:
            response = await ProviderChain.instance().complete(prompt, self._tools)
        except (httpx.HTTPError, RuntimeError) as e:
            logger.warning('agent_provider_failed', error=str(e))
            return self._fallback(data)

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

        if content.startswith('CLARIFY:'):
            question = content[len('CLARIFY:') :].strip()
            logger.info('agent_asking_clarification', question=question)
            return replace(data, text=f',clarify:{question}')

        if content.startswith('SUGGEST:'):
            suggestion = content[len('SUGGEST:') :].strip()
            logger.info('agent_suggesting_command', suggestion=suggestion)
            return replace(data, text=f',suggest:{suggestion}')

        logger.warning('agent_no_tool_call', content=content, tool_call=response.tool_call)
        return self._fallback(data)

    def _build_prompt(self, user_input: str, context: str | None = None) -> str:
        filtered_input = user_input.replace(self.BOT_MENTION_TAG, '').strip()[
            : self.MAX_USER_INPUT_LENGTH
        ]
        truncated_context = context[: self.MAX_CONTEXT_LENGTH] if context else None

        examples_text = '\n'.join(
            f'Usuário: "{prompt}" -> Comando: {cmd}'
            for prompt, cmd in AGENT_EXAMPLES[: self.MAX_AGENT_EXAMPLES]
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

    def _fallback(self, data: CommandData) -> CommandData:
        return replace(data, text='')
