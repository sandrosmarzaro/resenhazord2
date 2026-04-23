"""LLM Agent Executor - maps natural language to bot commands."""

import json

import httpx
import structlog

from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES, SYSTEM_PROMPT_TEMPLATE
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.provider_chain import get_chain
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    get_command_list_with_descriptions,
)

logger = structlog.get_logger()

FALLBACK_COMMAND = None
FALLBACK_MESSAGE = 'Não entendi. Tente usar um comando direto, ex: ,menu'


class AgentExecutor:
    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self._registry = registry or CommandRegistry.instance()

    async def run(self, data: CommandData) -> CommandData:
        """Execute agent: map natural language to command.

        Returns CommandData with rewritten text for command execution.
        """
        prompt = self._build_prompt(data.text)
        tools = build_tools_for_prompt(self._registry)

        logger.info(
            'agent_executing',
            user_input=data.text,
            tool_count=len(tools),
        )

        try:
            chain = get_chain()
            response = await chain.complete(prompt, tools)
        except (httpx.HTTPError, RuntimeError) as e:
            logger.warning('agent_provider_failed', error=str(e))
            return self._fallback(data)

        if response.tool_call:
            command_name = response.tool_call.get('name', '')
            arguments = response.tool_call.get('arguments', '{}')

            return self._build_command_data(data, command_name, arguments)

        content = response.content.strip().strip('`').strip('"\'').strip()
        if content.startswith((',', '/')):
            cmd = content.lstrip(',/').strip("'\"")
            return self._build_command_data(data, cmd, '')

        logger.warning(
            'agent_no_tool_call',
            content=content,
            tool_call=response.tool_call,
        )
        return self._fallback(data)

    def _build_prompt(self, user_input: str) -> str:
        """Build the prompt with tools and examples."""
        filtered_input = user_input.replace('@resenhazord', '').strip()

        command_list = get_command_list_with_descriptions(self._registry)

        examples_text = '\n'.join(
            f'Usuário: "{prompt}" -> Comando: {cmd}' for prompt, cmd in AGENT_EXAMPLES[:20]
        )

        return SYSTEM_PROMPT_TEMPLATE.format(
            command_list=command_list,
            examples=examples_text,
            user_input=filtered_input,
        )

    def _build_command_data(
        self,
        data: CommandData,
        command_name: str,
        arguments: str,
    ) -> CommandData:
        """Build new CommandData with mapped command."""
        try:
            args_dict = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            args_dict = {}

        flags = [k.lstrip('-') for k, v in args_dict.items() if v is True]
        options = {
            k.lstrip('-'): v
            for k, v in args_dict.items()
            if v is not True and v is not False and k != 'args'
        }
        text_args = args_dict.get('args', '')

        command_parts = [f',{command_name}']
        for flag in flags:
            command_parts.append(flag)
        for opt_name, opt_value in options.items():
            if isinstance(opt_value, str):
                command_parts.append(f'{opt_name} {opt_value}')
            else:
                command_parts.append(str(opt_value))
        if text_args:
            command_parts.append(text_args)

        command_text = ' '.join(command_parts).strip("'\"")

        logger.info(
            'agent_mapped_command',
            original=data.text,
            response_content=response.content,
            cleaned_content=response.content.strip("`'\"").strip(),
            mapped=command_text,
        )

        return CommandData(
            text=command_text,
            jid=data.jid,
            sender_jid=data.sender_jid,
            participant=data.participant,
            is_group=data.is_group,
            mentioned_jids=data.mentioned_jids,
            quoted_message_id=data.quoted_message_id,
            message_id=data.message_id,
            platform=data.platform,
        )

    def _fallback(self, data: CommandData) -> CommandData:
        """Return empty command to indicate no response."""
        return CommandData(
            text='',
            jid=data.jid,
            sender_jid=data.sender_jid,
            participant=data.participant,
            is_group=data.is_group,
            mentioned_jids=data.mentioned_jids,
            quoted_message_id=data.quoted_message_id,
            message_id=data.message_id,
            platform=data.platform,
        )

    def _clear_memory(self) -> None:
        """Clear any memory after execution (no-op for single-turn)."""
