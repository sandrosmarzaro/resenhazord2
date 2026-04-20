from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import ClassVar

import anyio

from bot.ports.telegram_port import TelegramPort


class TypingLoop:
    REFRESH_SECONDS: ClassVar[float] = 4.0

    @classmethod
    @asynccontextmanager
    async def keep_typing(cls, port: TelegramPort, chat_id: int) -> AsyncIterator[None]:
        await port.send_typing(chat_id)
        async with anyio.create_task_group() as tg:
            stop = anyio.Event()
            tg.start_soon(cls._run_loop, port, chat_id, stop)
            try:
                yield
            finally:
                stop.set()

    @classmethod
    async def _run_loop(cls, port: TelegramPort, chat_id: int, stop: anyio.Event) -> None:
        while not stop.is_set():
            with anyio.move_on_after(cls.REFRESH_SECONDS):
                await stop.wait()
            if stop.is_set():
                return
            await port.send_typing(chat_id)
