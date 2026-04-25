"""LLM Agent Executor - maps natural language to bot commands."""

import json
import re

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
MAX_AGENT_EXAMPLES = 20

DM_KEYWORDS = re.compile(
    r'\b(privado|pv|dm|direct|mp|message\s*privately|send\s*(me\s*)?dm|send\s*(me\s*)?privately)\b',
    re.IGNORECASE,
)


class AgentExecutor:
    def __init__(self, registry: CommandRegistry | None = None) -> None:
        self._registry = registry or CommandRegistry.instance()

    async def run(self, data: CommandData) -> CommandData:
        """Execute agent: map natural language to command.

        Returns CommandData with rewritten text for command execution.
        """
        prompt = self._build_prompt(data.text, context=data.quoted_text)
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
        content = re.sub(r'(\s)--(\w+)', r'\1\2', content)
        content = re.sub(r'^,+-', lambda m: ',' + m.group(1).lstrip('-'), content)

        if content.startswith((',', '/')):
            cmd = content.lstrip(',/').strip('\'"')
            return self._build_command_data(data, cmd, '')

        if content.startswith('CLARIFY:'):
            question = content[len('CLARIFY:') :].strip()
            logger.info('agent_asking_clarification', question=question)
            return CommandData(
                text=f',clarify:{question}',
                jid=data.jid,
                sender_jid=data.sender_jid,
                participant=data.participant,
                is_group=data.is_group,
                mentioned_jids=data.mentioned_jids,
                quoted_message_id=data.quoted_message_id,
                message_id=data.message_id,
                platform=data.platform,
                media_type=data.media_type,
                media_source=data.media_source,
                media_is_animated=data.media_is_animated,
                media_caption=data.media_caption,
                media_buffer=data.media_buffer,
            )

        if content.startswith('SUGGEST:'):
            suggestion = content[len('SUGGEST:') :].strip()
            logger.info('agent_suggesting_command', suggestion=suggestion)
            return CommandData(
                text=f',suggest:{suggestion}',
                jid=data.jid,
                sender_jid=data.sender_jid,
                participant=data.participant,
                is_group=data.is_group,
                mentioned_jids=data.mentioned_jids,
                quoted_message_id=data.quoted_message_id,
                message_id=data.message_id,
                platform=data.platform,
                media_type=data.media_type,
                media_source=data.media_source,
                media_is_animated=data.media_is_animated,
                media_caption=data.media_caption,
                media_buffer=data.media_buffer,
            )

        logger.warning(
            'agent_no_tool_call',
            content=content,
            tool_call=response.tool_call,
        )
        return self._fallback(data)

    def _build_prompt(self, user_input: str, context: str | None = None) -> str:
        """Build the prompt with tools and examples."""
        filtered_input = user_input.replace('@resenhazord', '').strip()

        command_list = get_command_list_with_descriptions(self._registry)

        examples_text = '\n'.join(
            f'Usuário: "{prompt}" -> Comando: {cmd}'
            for prompt, cmd in AGENT_EXAMPLES[:MAX_AGENT_EXAMPLES]
        )

        if context:
            context_block = f'\nContexto da mensagem anterior: "{context}"'
            user_block = f'\nPedido do usuário (respondendo acima): {filtered_input}'
        else:
            context_block = ''
            user_block = f'\nPedido do usuário: {filtered_input}'

        return SYSTEM_PROMPT_TEMPLATE.format(
            command_list=command_list,
            examples=examples_text,
            user_input=filtered_input,
            context=context_block,
            user_context=user_block,
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
        command_name = command_name.lstrip('-')
        options = {
            k.lstrip('-'): v
            for k, v in args_dict.items()
            if v is not True and v is not False and k not in ('args', 'command')
        }
        text_args = args_dict.get('args', '')

        command_parts = [f',{command_name}']
        for opt_name, opt_value in options.items():
            if isinstance(opt_value, str):
                command_parts.append(f'{opt_name} {opt_value}')
            else:
                command_parts.append(str(opt_value))
        for flag in flags:
            clean_flag = flag.lstrip('-')
            command_parts.append(clean_flag)
        if text_args:
            command_parts.append(text_args)

        command_text = ' '.join(command_parts).strip('\'"')
        command_text = self._resolve_command_name(command_text)

        target_jid = data.jid
        if data.is_group and DM_KEYWORDS.search(data.text):
            target_jid = data.sender_jid
            command_text = DM_KEYWORDS.sub('', command_text).strip()
            if command_text.startswith(','):
                command_text = command_text[1:].strip()
            command_text = f',{command_text}'

        command_text = re.sub(r'(\s)--(\w+)', r'\1\2', command_text)
        command_text = re.sub(r'^,+-', lambda m: ',' + m.group(1).lstrip('-'), command_text)

        logger.info(
            'agent_mapped_command',
            original=data.text,
            mapped=command_text,
            dm_mode=target_jid != data.jid,
        )

        return CommandData(
            text=command_text,
            jid=target_jid,
            sender_jid=data.sender_jid,
            participant=data.participant,
            is_group=data.is_group,
            mentioned_jids=data.mentioned_jids,
            quoted_message_id=data.quoted_message_id,
            message_id=data.message_id,
            platform=data.platform,
            media_type=data.media_type,
            media_source=data.media_source,
            media_is_animated=data.media_is_animated,
            media_caption=data.media_caption,
            media_buffer=data.media_buffer,
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
            media_type=data.media_type,
            media_source=data.media_source,
            media_is_animated=data.media_is_animated,
            media_caption=data.media_caption,
            media_buffer=data.media_buffer,
        )

    def _clear_memory(self) -> None:
        """Clear any memory after execution (no-op for single-turn)."""

    def _resolve_command_name(self, command_text: str) -> str:
        """Convert LLM command names to registered names using aliases."""
        if not command_text.startswith(','):
            return command_text

        parts = command_text.split()
        if not parts:
            return command_text

        cmd_name = parts[0][1:]
        cmd = self._registry.get_by_name(cmd_name)
        if cmd:
            parts[0] = f',{cmd.config.name}'
        return ' '.join(parts)
