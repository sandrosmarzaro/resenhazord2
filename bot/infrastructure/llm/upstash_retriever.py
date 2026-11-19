from typing import ClassVar

import structlog
from upstash_vector import AsyncIndex
from upstash_vector.types import Data

from bot.domain.models.retrieved_example import RetrievedExample

logger = structlog.get_logger()


class UpstashExampleRetriever:
    _RANGE_PAGE_SIZE: ClassVar[int] = 500

    def __init__(self, index: AsyncIndex) -> None:
        self._index = index

    @classmethod
    def from_credentials(cls, url: str, token: str) -> 'UpstashExampleRetriever':
        return cls(AsyncIndex(url=url, token=token))

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedExample]:
        results = await self._index.query(
            data=query, top_k=top_k, include_metadata=True, include_data=True
        )
        return [
            RetrievedExample(
                text=result.data, command=result.metadata['command'], score=result.score
            )
            for result in results
            if result.data is not None and result.metadata is not None
        ]

    async def index_examples(self, examples: list[RetrievedExample]) -> None:
        await self._index.upsert(
            vectors=[
                Data(id=example.text, data=example.text, metadata={'command': example.command})
                for example in examples
            ]
        )
        stale_ids = await self._indexed_ids() - {example.text for example in examples}
        if stale_ids:
            await self._index.delete(ids=sorted(stale_ids))
        logger.info('example_bank_indexed', upserted=len(examples), deleted=len(stale_ids))

    async def _indexed_ids(self) -> set[str]:
        ids: set[str] = set()
        cursor = ''
        while True:
            page = await self._index.range(cursor=cursor, limit=self._RANGE_PAGE_SIZE)
            ids.update(vector.id for vector in page.vectors)
            if not page.next_cursor:
                return ids
            cursor = page.next_cursor
