import os

import pytest

from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever

UPSTASH_URL = os.environ.get('UPSTASH_VECTOR_REST_URL')
UPSTASH_TOKEN = os.environ.get('UPSTASH_VECTOR_REST_TOKEN')

pytestmark = [
    pytest.mark.external,
    pytest.mark.skipif(
        not UPSTASH_URL or not UPSTASH_TOKEN,
        reason='Upstash Vector credentials absent',
    ),
]


# Read-only: index_examples prunes every id outside the given bank, so indexing a
# fixture here would wipe the shared index. It queries the bank index:examples built.
class TestRetrieve:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_retrieves_the_most_similar_bank_example_first(self):
        assert UPSTASH_URL is not None
        assert UPSTASH_TOKEN is not None

        retriever = UpstashExampleRetriever.from_credentials(UPSTASH_URL, UPSTASH_TOKEN)

        results = await retriever.retrieve('placar dos jogos agora', top_k=1)

        assert results[0].command == ',score --now'
