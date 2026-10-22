import json
from typing import ClassVar

import httpx
import sentry_sdk
import structlog

from bot.application.agent_response import AgentResponseTranslator
from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import SYSTEM_PROMPT_TEMPLATE
from bot.data.agent_meta_tools import (
    AGENT_META_TOOLS,
    CONFIDENCE_ARG,
    CONFIDENCE_PROPERTY,
    META_TOOL_TEXT,
)
from bot.domain.constants import AGENT_MENU_HINT, BOT_MENTION_TAG, MAX_USER_INPUT_LENGTH
from bot.domain.models.agent_decision import AgentDecision, AgentOutcome
from bot.domain.models.command_data import CommandData
from bot.domain.models.llm_response import LLMResponse
from bot.domain.models.retrieved_example import RetrievedExample
from bot.domain.models.system_prompt import SystemPrompt
from bot.infrastructure.llm.tools import (
    build_tools_for_prompt,
    get_command_list_with_descriptions,
)
from bot.ports.llm_provider_port import LLMProviderPort
from bot.ports.prompt_registry_port import PromptRegistryError, PromptRegistryPort

logger = structlog.get_logger()


class LLMCommandMapper:
    """Asks the LLM which command a request means and returns that as a decision."""

    CONFIDENCE_THRESHOLD: ClassVar[float] = 0.7
    MAX_CONTEXT_LENGTH: ClassVar[int] = 2000
    UNAVAILABLE_MSG: ClassVar[str] = f'🤖 IA indisponível no momento. {AGENT_MENU_HINT}'
    UNRESOLVABLE_MSG: ClassVar[str] = f'🤖 Não consegui entender. {AGENT_MENU_HINT}'
    _UNAVAILABLE_EVENT: ClassVar[str] = 'agent_unavailable'

    def __init__(
        self,
        registry: CommandRegistry,
        provider: LLMProviderPort,
        prompt_registry: PromptRegistryPort | None = None,
    ) -> None:
        self._provider = provider
        self._prompt_registry = prompt_registry
        self._tools = self._with_confidence(build_tools_for_prompt(registry)) + AGENT_META_TOOLS
        self._command_list = get_command_list_with_descriptions(registry)
        self._translator = AgentResponseTranslator(registry)

    async def map(self, data: CommandData, examples: list[RetrievedExample]) -> AgentDecision:
        logger.info('agent_executing', user_input=data.text, tool_count=len(self._tools))
        version = ''
        try:
            system_prompt = self._system_prompt()
            version = system_prompt.version
            prompt = self._build_prompt(system_prompt.template, data, examples)
            response = await self._provider.complete(prompt, self._tools)
        except (httpx.HTTPError, RuntimeError, PromptRegistryError) as error:
            logger.warning('agent_provider_failed', error=str(error))
            # Per-provider 429s are filtered as noise, so this is the only Sentry signal
            # that the user got no answer. A plain message keeps the log's bound jid/sender
            # out of the issue title and groups the whole outage into one issue.
            sentry_sdk.capture_message(self._UNAVAILABLE_EVENT, level='error')
            return AgentDecision(
                AgentOutcome.UNAVAILABLE, text=self.UNAVAILABLE_MSG, prompt_version=version
            )
        decision = self._interpret(data, response)
        return AgentDecision(
            decision.outcome,
            command=decision.command,
            text=decision.text,
            provider=response.provider,
            prompt_version=version,
        )

    def _system_prompt(self) -> SystemPrompt:
        if self._prompt_registry:
            return self._prompt_registry.system_prompt()
        return SystemPrompt(template=SYSTEM_PROMPT_TEMPLATE, version='')

    def _interpret(self, data: CommandData, response: LLMResponse) -> AgentDecision:
        if response.tool_call:
            return self._route_tool_call(data, response.tool_call)

        content = AgentResponseTranslator.normalize_flags(
            response.content.strip().strip('`').strip('"\'').strip()
        )
        if content.startswith((',', '/')):
            command = content.lstrip(',/').strip('\'"')
            return AgentDecision(AgentOutcome.COMMAND, command=f',{command}')

        logger.warning('agent_no_tool_call', content=content, tool_call=response.tool_call)
        return self._unresolvable()

    def _route_tool_call(self, data: CommandData, tool_call: dict) -> AgentDecision:
        name = tool_call.get('name', '')
        arguments = tool_call.get('arguments', '{}')
        if name in META_TOOL_TEXT:
            return self._meta(name, arguments)
        command = self._translator.compose(name, arguments)
        if self._confidence(arguments) >= self.CONFIDENCE_THRESHOLD:
            return AgentDecision(AgentOutcome.COMMAND, command=command)
        proposed = AgentResponseTranslator.normalize_flags(command)
        logger.info('agent_confirming', proposed=proposed, original=data.text)
        return AgentDecision(
            AgentOutcome.CONFIRM, command=proposed, text=f'Você quis dizer `{proposed}`?'
        )

    def _meta(self, name: str, arguments: str) -> AgentDecision:
        argument, event, log_field = META_TOOL_TEXT[name]
        text = self._tool_arg(arguments, argument)
        if not text:
            return self._unresolvable()
        logger.info(event, **{log_field: text})
        # Meta-tool names double as their outcome values.
        return AgentDecision(AgentOutcome(name), text=text)

    def _unresolvable(self) -> AgentDecision:
        return AgentDecision(AgentOutcome.UNRESOLVABLE, text=self.UNRESOLVABLE_MSG)

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

    @staticmethod
    def _tool_arg(arguments: str, key: str) -> str:
        try:
            return str(json.loads(arguments).get(key, '')).strip()
        except json.JSONDecodeError:
            return ''

    def _build_prompt(
        self, template: str, data: CommandData, examples: list[RetrievedExample]
    ) -> str:
        user_input = data.text.replace(BOT_MENTION_TAG, '').strip()[:MAX_USER_INPUT_LENGTH]
        examples_text = '\n'.join(
            f'Usuário: "{example.text}" -> Comando: {example.command}' for example in examples
        )
        context = (data.quoted_text or '')[: self.MAX_CONTEXT_LENGTH]
        if context:
            context_block = f'\nContexto da mensagem anterior: "{context}"'
            user_block = f'\nPedido do usuário (respondendo acima): {user_input}'
        else:
            context_block = ''
            user_block = f'\nPedido do usuário: {user_input}'
        return template.format(
            command_list=self._command_list,
            examples=examples_text,
            user_input=user_input,
            context=context_block,
            user_context=user_block,
        )
