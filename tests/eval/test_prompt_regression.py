import pytest

from bot.application.agent_executor import AgentExecutor
from bot.application.register_commands import register_all_commands
from bot.domain.models.command_data import CommandData
from bot.settings import Settings
from tests.eval.dataset import PROMPT_REGRESSION_CASES

_ACCURACY_THRESHOLD = 0.7


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.eval
@pytest.mark.anyio
async def test_prompt_maps_held_out_requests_above_threshold():
    settings = Settings()
    if not (settings.github_token or settings.mistral_api_key or settings.groq_api_key):
        pytest.skip('no LLM provider configured; set a provider key to run the prompt eval')

    register_all_commands(settings)
    executor = AgentExecutor()

    misses = []
    for text, expected in PROMPT_REGRESSION_CASES:
        result = await executor.run(_data(text))
        if not result.text.startswith(expected):
            misses.append(f'{text!r} -> {result.text!r} (wanted {expected!r})')

    accuracy = 1 - len(misses) / len(PROMPT_REGRESSION_CASES)
    report = '\n'.join(misses)
    assert accuracy >= _ACCURACY_THRESHOLD, (
        f'accuracy {accuracy:.0%} below {_ACCURACY_THRESHOLD:.0%}\n{report}'
    )


def _data(text: str) -> CommandData:
    return CommandData(text=text, jid='eval@g.us', sender_jid='eval@s.whatsapp.net')
