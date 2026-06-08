from bot.ports.broker_port import MessageHandler


class MockBrokerPort:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self._handlers: dict[str, MessageHandler] = {}

    async def connect(self, url: str) -> None:
        return None

    async def publish(self, queue: str, body: bytes) -> None:
        self.published.append((queue, body))

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        self._handlers[queue] = handler

    async def close(self) -> None:
        return None

    async def deliver(self, queue: str, body: bytes) -> None:
        await self._handlers[queue](body)
