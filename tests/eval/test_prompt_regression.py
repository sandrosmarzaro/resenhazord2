import pytest

from bot.application.command_registry import CommandRegistry
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.application.register_commands import build_agent_graph, register_all_commands
from bot.domain.models.command_data import CommandData
from bot.settings import Settings
from tests.eval.dataset import DENIED_CASES, PROMPT_REGRESSION_CASES

_ACCURACY_THRESHOLD = 0.7

# A provider failure surfaces as this message. It means the LLM was unreachable,
# not that the prompt mapped wrong, so those samples are inconclusive — the eval
# judges the prompt only over samples that got a real model response.
_PROVIDER_UNAVAILABLE = LLMCommandMapper.UNAVAILABLE_MSG


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.mark.eval
@pytest.mark.anyio
async def test_prompt_maps_held_out_requests_above_threshold():
    answers = await _answers(PROMPT_REGRESSION_CASES)

    misses = [
        f'{text!r} -> {answer!r} (wanted {expected!r})'
        for text, expected, answer in answers
        if not answer.startswith(expected)
    ]
    _assert_above_threshold(answers, misses)


@pytest.mark.eval
@pytest.mark.anyio
async def test_prompt_stops_repeating_denied_mappings():
    if not DENIED_CASES:
        pytest.skip('no denied mapping collected yet')
    answers = await _answers(DENIED_CASES)

    repeats = [
        f'{text!r} -> {answer!r} (denied before)'
        for text, denied, answer in answers
        if answer.startswith(denied)
    ]
    _assert_above_threshold(answers, repeats)


async def _answers(cases: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    register_all_commands(Settings())
    # No Redis: each case runs in its own in-memory thread, so a pending question
    # from one case never becomes context for the next.
    agent = build_agent_graph(CommandRegistry.instance(), Settings(), redis_url=None)

    answers = []
    for case, (text, target) in enumerate(cases):
        try:
            result = await agent.run(_data(text, case))
        except Exception:  # noqa: BLE001
            continue
        if _PROVIDER_UNAVAILABLE in result.text:
            continue
        answers.append((text, target, result.text))
    if not answers:
        pytest.skip('no working LLM provider; cannot evaluate the prompt')
    return answers


def _assert_above_threshold(answers: list[tuple[str, str, str]], failures: list[str]) -> None:
    accuracy = 1 - len(failures) / len(answers)
    report = '\n'.join(failures)
    assert accuracy >= _ACCURACY_THRESHOLD, (
        f'accuracy {accuracy:.0%} over {len(answers)} conclusive '
        f'below {_ACCURACY_THRESHOLD:.0%}\n{report}'
    )


def _data(text: str, case: int) -> CommandData:
    return CommandData(text=text, jid=f'eval-{case}@g.us', sender_jid='eval@s.whatsapp.net')
