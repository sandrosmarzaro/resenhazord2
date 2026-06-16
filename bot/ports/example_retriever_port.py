from typing import Protocol

from bot.domain.models.retrieved_example import RetrievedExample


class ExampleRetrieverPort(Protocol):
    async def retrieve(self, query: str, top_k: int) -> list[RetrievedExample]: ...
