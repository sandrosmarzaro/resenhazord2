from bot.ports.broker_port import MessageHandler


class MockBrokerPort:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.declared: list[str] = []
        self.retry_queues: list[tuple[str, int, str]] = []
        self.connected_urls: list[str] = []
        self.rpc_calls: list[tuple[str, bytes]] = []
        self.rpc_response: bytes = b'{}'
        self._handlers: dict[str, MessageHandler] = {}

    async def connect(self, url: str) -> None:
        self.connected_urls.append(url)

    async def rpc_call(self, queue: str, body: bytes) -> bytes:
        self.rpc_calls.append((queue, body))
        return self.rpc_response

    async def declare(self, queue: str) -> None:
        self.declared.append(queue)

    async def declare_retry_queue(self, queue: str, ttl_ms: int, dead_letter_to: str) -> None:
        self.declared.append(queue)
        self.retry_queues.append((queue, ttl_ms, dead_letter_to))

    async def publish(self, queue: str, body: bytes) -> None:
        self.published.append((queue, body))

    async def consume(self, queue: str, handler: MessageHandler) -> None:
        self._handlers[queue] = handler

    async def close(self) -> None:
        return None

    async def deliver(self, queue: str, body: bytes) -> None:
        await self._handlers[queue](body)
