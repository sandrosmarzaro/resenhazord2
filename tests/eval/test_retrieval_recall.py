import pytest

from bot.application.example_selector import ExampleSelector
from bot.application.register_commands import register_all_commands
from bot.infrastructure.llm.agent_feedback import AgentFeedback
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.settings import Settings
from tests.eval.dataset import PROMPT_REGRESSION_CASES
from tests.eval.grafana import publish_gauge

_RECALL_THRESHOLD = 0.8


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.eval
@pytest.mark.anyio
async def test_retrieval_surfaces_the_expected_command_above_threshold():
    settings = Settings()
    if not settings.upstash_vector_rest_url:
        pytest.skip('no Upstash index; cannot evaluate retrieval')
    register_all_commands(settings)
    retriever = UpstashExampleRetriever.from_credentials(
        settings.upstash_vector_rest_url, settings.upstash_vector_rest_token
    )
    selector = ExampleSelector(retriever)

    misses = []
    for text, expected in PROMPT_REGRESSION_CASES:
        retrieved = [example.command for example in await selector.select(text)]
        if not AgentFeedback.recalls(retrieved, expected):
            misses.append(f'{text!r} -> {retrieved} (wanted {expected!r})')

    recall = 1 - len(misses) / len(PROMPT_REGRESSION_CASES)
    k = ExampleSelector.MAX_EXAMPLES
    publish_gauge('agent.eval.recall', recall, {'k': str(k)})
    report = '\n'.join(misses)
    assert recall >= _RECALL_THRESHOLD, (
        f'recall@{k} {recall:.0%} below {_RECALL_THRESHOLD:.0%}\n{report}'
    )
