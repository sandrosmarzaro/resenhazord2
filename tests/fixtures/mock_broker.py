from bot.ports.broker_port import Delivery, DeliveryRejectedError, MessageHandler


class MockBrokerPort:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.rejected: list[tuple[str, bytes]] = []
        self.connected_urls: list[str] = []
        self.rpc_calls: list[tuple[str, bytes]] = []
        self.rpc_response: bytes = b'{}'
        self._handlers: dict[str, MessageHandler] = {}

    async def connect(self, url: str) -> None:
        self.connected_urls.append(url)

    async def rpc_call(self, queue: str, body: bytes) -> bytes:
        self.rpc_calls.append((queue, body))
        return self.rpc_response

    async def publish(self, queue: str, body: bytes) -> None:
        self.published.append((queue, body))

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        self._handlers[queue] = handler

    async def close(self) -> None:
        return None

    async def deliver(self, queue: str, body: bytes, attempt: int = 1) -> None:
        try:
            await self._handlers[queue](Delivery(body, attempt))
        except DeliveryRejectedError:
            self.rejected.append((queue, body))
