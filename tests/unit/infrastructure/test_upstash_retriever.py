import json

import httpx
import pytest
from structlog.testing import capture_logs

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


def _range_page(ids: list[str], next_cursor: str) -> httpx.Response:
    vectors = [{'id': vector_id} for vector_id in ids]
    return httpx.Response(200, json={'result': {'nextCursor': next_cursor, 'vectors': vectors}})


class TestIndexExamples:
    @pytest.fixture
    def retriever(self) -> UpstashExampleRetriever:
        return UpstashExampleRetriever.from_credentials(_INDEX_URL, 'token')

    @pytest.fixture
    def upsert_route(self, respx_mock):
        return respx_mock.post(f'{_INDEX_URL}/upsert-data').mock(
            return_value=httpx.Response(200, json={'result': 'Success'})
        )

    @pytest.fixture
    def delete_route(self, respx_mock):
        return respx_mock.post(f'{_INDEX_URL}/delete').mock(
            return_value=httpx.Response(200, json={'result': {'deleted': 1}})
        )

    @pytest.mark.anyio
    async def test_deletes_ids_missing_from_the_bank(
        self, retriever, respx_mock, upsert_route, delete_route
    ):
        respx_mock.post(f'{_INDEX_URL}/range').mock(
            return_value=_range_page(['time do flamengo', 'scarra'], next_cursor='')
        )

        await retriever.index_examples(
            [RetrievedExample(text='time do flamengo', command=',time flamengo')]
        )

        assert json.loads(delete_route.calls.last.request.content) == {'ids': ['scarra']}

    @pytest.mark.anyio
    async def test_finds_stale_ids_on_every_page(
        self, retriever, respx_mock, upsert_route, delete_route
    ):
        respx_mock.post(f'{_INDEX_URL}/range').mock(
            side_effect=[
                _range_page(['time do flamengo'], next_cursor='1'),
                _range_page(['scarra'], next_cursor=''),
            ]
        )

        await retriever.index_examples(
            [RetrievedExample(text='time do flamengo', command=',time flamengo')]
        )

        assert json.loads(delete_route.calls.last.request.content) == {'ids': ['scarra']}

    @pytest.mark.anyio
    async def test_deletes_nothing_when_the_index_matches_the_bank(
        self, retriever, respx_mock, upsert_route, delete_route
    ):
        respx_mock.post(f'{_INDEX_URL}/range').mock(
            return_value=_range_page(['time do flamengo'], next_cursor='')
        )

        await retriever.index_examples(
            [RetrievedExample(text='time do flamengo', command=',time flamengo')]
        )

        assert not delete_route.called

    @pytest.mark.anyio
    async def test_logs_upserted_and_deleted_counts(
        self, retriever, respx_mock, upsert_route, delete_route
    ):
        respx_mock.post(f'{_INDEX_URL}/range').mock(
            return_value=_range_page(['time do flamengo', 'scarra'], next_cursor='')
        )

        with capture_logs() as logs:
            await retriever.index_examples(
                [RetrievedExample(text='time do flamengo', command=',time flamengo')]
            )

        assert [
            (log['upserted'], log['deleted'])
            for log in logs
            if log['event'] == 'example_bank_indexed'
        ] == [(1, 1)]
