import os

import pytest

from bot.domain.models.retrieved_example import RetrievedExample
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


class TestRetrieveRoundTrip:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_indexes_and_retrieves_most_similar_first(self):
        assert UPSTASH_URL is not None
        assert UPSTASH_TOKEN is not None

        retriever = UpstashExampleRetriever.from_credentials(UPSTASH_URL, UPSTASH_TOKEN)
        await retriever.index_examples(
            [
                RetrievedExample(text='ver o placar do jogo', command=',score --now'),
                RetrievedExample(text='me manda um carro aleatório', command=',carro'),
            ]
        )

        results = await retriever.retrieve('placar dos jogos agora', top_k=1)

        assert results[0].command == ',score --now'
