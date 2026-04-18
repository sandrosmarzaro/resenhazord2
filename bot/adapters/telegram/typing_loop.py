from contextlib import asynccontextmanager
from typing import Final

import anyio

from bot.ports.telegram_port import TelegramPort

TYPING_REFRESH_SECONDS: Final[float] = 4.0


@asynccontextmanager
async def keep_typing(port: TelegramPort, chat_id: int):
    await port.send_typing(chat_id)
    async with anyio.create_task_group() as tg:
        stop = anyio.Event()
        tg.start_soon(_run_loop, port, chat_id, stop)
        try:
            yield
        finally:
            stop.set()


async def _run_loop(port: TelegramPort, chat_id: int, stop: anyio.Event) -> None:
    while not stop.is_set():
        with anyio.move_on_after(TYPING_REFRESH_SECONDS):
            await stop.wait()
        if stop.is_set():
            return
        await port.send_typing(chat_id)
