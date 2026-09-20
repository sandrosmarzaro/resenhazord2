import pytest

from bot.application.agent_executor import AgentExecutor
from bot.application.register_commands import register_all_commands
from bot.domain.models.command_data import CommandData
from bot.settings import Settings
from tests.eval.dataset import PROMPT_REGRESSION_CASES

_ACCURACY_THRESHOLD = 0.7

# A provider failure surfaces as this message. It means the LLM was unreachable,
# not that the prompt mapped wrong, so those samples are inconclusive — the eval
# judges the prompt only over samples that got a real model response.
_PROVIDER_UNAVAILABLE = AgentExecutor._AGENT_UNAVAILABLE_MSG


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.eval
@pytest.mark.anyio
async def test_prompt_maps_held_out_requests_above_threshold():
    register_all_commands(Settings())
    executor = AgentExecutor()

    hits = 0
    conclusive = 0
    misses = []
    for text, expected in PROMPT_REGRESSION_CASES:
        try:
            result = await executor.run(_data(text))
        except Exception:  # noqa: BLE001
            continue
        if _PROVIDER_UNAVAILABLE in result.text:
            continue
        conclusive += 1
        if result.text.startswith(expected):
            hits += 1
        else:
            misses.append(f'{text!r} -> {result.text!r} (wanted {expected!r})')

    if conclusive == 0:
        pytest.skip('no working LLM provider; cannot evaluate the prompt')

    accuracy = hits / conclusive
    report = '\n'.join(misses)
    assert accuracy >= _ACCURACY_THRESHOLD, (
        f'accuracy {accuracy:.0%} over {conclusive} conclusive '
        f'below {_ACCURACY_THRESHOLD:.0%}\n{report}'
    )


def _data(text: str) -> CommandData:
    return CommandData(text=text, jid='eval@g.us', sender_jid='eval@s.whatsapp.net')
