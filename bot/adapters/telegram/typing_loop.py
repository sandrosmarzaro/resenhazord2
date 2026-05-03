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
        stop = anyio.Event()

        async def _send_loop() -> None:
            while not stop.is_set():
                with anyio.move_on_after(cls.REFRESH_SECONDS):
                    await stop.wait()
                if not stop.is_set():
                    await port.send_typing(chat_id)

        async with anyio.create_task_group() as tg:
            tg.start_soon(_send_loop)
            try:
                yield
            finally:
                stop.set()
