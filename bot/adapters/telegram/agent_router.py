from typing import ClassVar

import structlog
from telegram import Chat, Message

from bot.adapters.telegram.renderer import TelegramResponseRenderer
from bot.adapters.telegram.typing_loop import TypingLoop
from bot.application.agent_executor import AgentExecutor
from bot.application.command_registry import CommandRegistry
from bot.application.message_preprocess import preprocess_for_telegram
from bot.domain.commands.base import Command
from bot.domain.exceptions import BotError
from bot.domain.models.command_data import CommandData
from bot.ports.telegram_port import TelegramKind, TelegramOutbound, TelegramPort

logger = structlog.get_logger()


class TelegramAgentRouter:
    UNKNOWN_COMMAND_MESSAGE: ClassVar[str] = 'Comando nao reconhecido.'
    GENERIC_ERROR_MESSAGE: ClassVar[str] = 'Ocorreu um erro ao executar o comando.'
    EMPTY_REPLY_MESSAGE: ClassVar[str] = 'Sem resposta do bot.'
    ACK_REACTION: ClassVar[str] = '\U0001f44d'

    def __init__(self, renderer: TelegramResponseRenderer) -> None:
        self._renderer = renderer

    async def route(
        self,
        port: TelegramPort,
        message: Message,
        chat: Chat,
        data: CommandData,
    ) -> None:
        await self.safe_react(port, chat.id, message.message_id)
        async with TypingLoop.keep_typing(port, chat.id):
            result = await self._run_agent(port, chat.id, data)
            if result is None:
                return
            strategy = CommandRegistry.instance().get_strategy(result.text)
            if strategy is None:
                await self._reply_text(port, chat.id, self.UNKNOWN_COMMAND_MESSAGE)
                return
            await self.run_and_reply(port, strategy, result, chat.id, result.text)

    async def run_and_reply(
        self,
        port: TelegramPort,
        strategy: Command,
        data: CommandData,
        chat_id: int,
        command_name: str,
    ) -> None:
        try:
            messages = await strategy.run(data)
        except BotError as error:
            await self._reply_text(port, chat_id, error.user_message)
            return
        except Exception:
            logger.exception('telegram_command_error', command=command_name)
            await self._reply_text(port, chat_id, self.GENERIC_ERROR_MESSAGE)
            return

        if not messages:
            await self._reply_text(port, chat_id, self.EMPTY_REPLY_MESSAGE)
            return

        await self._send_messages(port, messages, chat_id, command_name)

    @classmethod
    async def safe_react(cls, port: TelegramPort, chat_id: int, message_id: int) -> None:
        try:
            await port.react(chat_id, message_id, cls.ACK_REACTION)
        except Exception:
            logger.exception('telegram_react_failed', chat_id=chat_id, message_id=message_id)

    async def _run_agent(
        self, port: TelegramPort, chat_id: int, data: CommandData
    ) -> CommandData | None:
        try:
            executor = AgentExecutor(CommandRegistry.instance())
            return await executor.run(data)
        except Exception:
            logger.exception('telegram_agent_error')
            await self._reply_text(port, chat_id, self.GENERIC_ERROR_MESSAGE)
            return None

    async def _send_messages(
        self,
        port: TelegramPort,
        messages: list,
        chat_id: int,
        command_name: str,
    ) -> None:
        prepared = await preprocess_for_telegram(messages)
        for outbound in self._renderer.render_many(prepared, chat_id):
            try:
                await port.send(outbound)
            except Exception:
                logger.exception('telegram_send_failed', command=command_name)
                await self._reply_text(port, chat_id, self.GENERIC_ERROR_MESSAGE)
                return

    @staticmethod
    async def _reply_text(port: TelegramPort, chat_id: int, text: str) -> None:
        await port.send(TelegramOutbound(kind=TelegramKind.TEXT, chat_id=chat_id, text=text))

    @staticmethod
    def is_agent_mention(message: Message, bot_username: str) -> bool:
        if not message.text or not bot_username:
            return False
        return f'@{bot_username}' in message.text.lower()
