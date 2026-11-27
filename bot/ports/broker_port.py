from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Delivery:
    body: bytes
    # Counts this run: 1, plus each time this queue already rejected the message.
    attempt: int = 1


class DeliveryRejectedError(Exception):
    """Rejects the delivery without requeue, so the queue's dead-letter route takes it."""


MessageHandler = Callable[[Delivery], Awaitable[None]]
RpcHandler = Callable[[bytes], Awaitable[bytes]]


class BrokerPort(Protocol):
    async def connect(self, url: str) -> None: ...

    async def publish(self, queue: str, body: bytes) -> None: ...

    async def consume(self, queue: str, handler: MessageHandler) -> None: ...

    async def rpc_call(self, queue: str, body: bytes) -> bytes: ...

    async def close(self) -> None: ...
