import httpx
import pytest

from bot.application.example_selector import ExampleSelector
from bot.data.agent_examples import AGENT_EXAMPLES
from bot.domain.models.command_data import CommandData
from bot.domain.models.retrieved_example import RetrievedExample
from tests.fixtures.fake_example_retriever import FakeExampleRetriever

_IDENTICAL = RetrievedExample(text='time do flamengo', command=',time flamengo', score=0.999)
_PARAPHRASE = RetrievedExample(text='me mande um carro', command=',carro', score=0.948)


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def _retriever(mocker, examples: list[RetrievedExample]):
    retriever = mocker.Mock()
    retriever.retrieve = mocker.AsyncMock(return_value=examples)
    return retriever


def _data(text: str, *, quoted_text: str | None = None) -> CommandData:
    return CommandData(
        text=text, jid='test@g.us', sender_jid='test@s.whatsapp.net', quoted_text=quoted_text
    )


class TestSelect:
    @pytest.mark.anyio
    async def test_returns_the_static_slice_without_a_retriever(self):
        examples = await ExampleSelector(None).select('qualquer pedido')

        assert examples == [
            RetrievedExample(text=text, command=command) for text, command in AGENT_EXAMPLES[:5]
        ]

    @pytest.mark.anyio
    async def test_queries_without_the_bot_mention(self):
        retriever = FakeExampleRetriever()
        retriever.index('quero ver o placar agora', ',score --now')
        retriever.index('me manda um carro', ',carro')

        examples = await ExampleSelector(retriever).select('@resenhazord quero ver o placar agora')

        assert examples == [
            RetrievedExample(text='quero ver o placar agora', command=',score --now', score=1.0)
        ]

    @pytest.mark.anyio
    async def test_asks_for_five_examples(self, mocker):
        retriever = _retriever(mocker, [])

        await ExampleSelector(retriever).select('placar agora')

        retriever.retrieve.assert_awaited_once_with('placar agora', 5)

    @pytest.mark.anyio
    async def test_drops_examples_below_the_similarity_floor(self, mocker):
        relevant = RetrievedExample(text='time do flamengo', command=',time flamengo', score=0.912)
        noise = RetrievedExample(text='fato aleatório', command=',fato', score=0.709)

        examples = await ExampleSelector(_retriever(mocker, [relevant, noise])).select('time')

        assert examples == [relevant]

    @pytest.mark.anyio
    async def test_falls_back_to_the_static_slice_on_retrieval_error(self, mocker):
        retriever = mocker.Mock()
        retriever.retrieve = mocker.AsyncMock(side_effect=httpx.ConnectError('upstash down'))

        examples = await ExampleSelector(retriever).select('placar agora')

        assert examples == await ExampleSelector(None).select('placar agora')


class TestDirectMatch:
    def test_near_identical_example_is_a_direct_match(self):
        match = ExampleSelector(None).direct_match(_data('time do flamengo'), [_IDENTICAL])

        assert match == _IDENTICAL

    def test_paraphrase_is_not_a_direct_match(self):
        match = ExampleSelector(None).direct_match(_data('me manda um carro'), [_PARAPHRASE])

        assert match is None

    def test_reply_to_a_question_is_never_a_direct_match(self):
        data = _data('time do flamengo', quoted_text='Quer a tabela ou o time?')

        assert ExampleSelector(None).direct_match(data, [_IDENTICAL]) is None

    def test_no_examples_is_no_match(self):
        assert ExampleSelector(None).direct_match(_data('oi'), []) is None
