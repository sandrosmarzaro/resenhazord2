import httpx
import pytest

from bot.domain.models.retrieved_example import RetrievedExample
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever

_INDEX_URL = 'https://index.upstash.io'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


class TestRetrieve:
    @pytest.mark.anyio
    async def test_carries_the_similarity_score(self, respx_mock):
        respx_mock.post(f'{_INDEX_URL}/query-data').mock(
            return_value=httpx.Response(
                200,
                json={
                    'result': [
                        {
                            'id': 'time do flamengo',
                            'score': 0.912,
                            'data': 'time do flamengo',
                            'metadata': {'command': ',time flamengo'},
                        }
                    ]
                },
            )
        )
        retriever = UpstashExampleRetriever.from_credentials(_INDEX_URL, 'token')

        examples = await retriever.retrieve('time do flamengo', top_k=5)

        assert examples == [
            RetrievedExample(text='time do flamengo', command=',time flamengo', score=0.912)
        ]
