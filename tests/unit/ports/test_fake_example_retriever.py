import pytest

from tests.fixtures.fake_example_retriever import FakeExampleRetriever


@pytest.fixture
def retriever() -> FakeExampleRetriever:
    retriever = FakeExampleRetriever()
    retriever.index('ver o placar do jogo', ',time')
    retriever.index('quero ouvir uma musica', ',musica')
    retriever.index('me manda um sticker', ',fig')
    return retriever


class TestRetrieve:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_ranks_most_similar_first(self, retriever):
        results = await retriever.retrieve('placar do jogo agora', top_k=3)

        assert results[0].command == ',time'

    @pytest.mark.anyio
    async def test_caps_results_at_top_k(self, retriever):
        retriever.index('placar do jogo ao vivo', ',time')

        results = await retriever.retrieve('placar do jogo', top_k=1)

        assert len(results) == 1

    @pytest.mark.anyio
    async def test_excludes_examples_with_no_overlap(self, retriever):
        results = await retriever.retrieve('placar', top_k=5)

        commands = [example.command for example in results]
        assert commands == [',time']
