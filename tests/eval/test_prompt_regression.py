import pytest

from bot.application.command_registry import CommandRegistry
from bot.application.llm_command_mapper import LLMCommandMapper
from bot.application.register_commands import build_agent_graph, register_all_commands
from bot.domain.models.command_data import CommandData
from bot.infrastructure.llm.langsmith_prompt_registry import LangSmithPromptRegistry
from bot.ports.prompt_registry_port import PromptRegistryError
from bot.settings import Settings
from tests.eval.dataset import DENIED_CASES, PROMPT_REGRESSION_CASES

_ACCURACY_THRESHOLD = 0.7

# A provider failure surfaces as this message. It means the LLM was unreachable,
# not that the prompt mapped wrong, so those samples are inconclusive — the eval
# judges the prompt only over samples that got a real model response.
_PROVIDER_UNAVAILABLE = LLMCommandMapper.UNAVAILABLE_MSG
_SERVED_TAG = 'prod'
_FALLBACK_TAG = 'dev'


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
    settings = _with_pullable_prompt(Settings())
    register_all_commands(settings)
    # No Redis: each case runs in its own in-memory thread, so a pending question
    # from one case never becomes context for the next.
    agent = build_agent_graph(CommandRegistry.instance(), settings, redis_url=None)

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


def _with_pullable_prompt(settings: Settings) -> Settings:
    # The eval judges the prompt the bot serves, falling back to dev while prod is
    # unpublished. A tag that can't be pulled is a broken setup, not a provider
    # outage, so it fails the eval instead of skipping every case.
    if not settings.langsmith_api_key:
        return settings
    tags = [settings.langsmith_prompt_tag]
    if settings.langsmith_prompt_tag == _SERVED_TAG:
        tags.append(_FALLBACK_TAG)
    errors = []
    for tag in tags:
        registry = LangSmithPromptRegistry.from_credentials(
            settings.langsmith_api_key, settings.langsmith_prompt_name, tag
        )
        try:
            registry.system_prompt()
        except PromptRegistryError as error:
            errors.append(f'{tag}: {error}')
            continue
        return settings.model_copy(update={'langsmith_prompt_tag': tag})
    pytest.fail(f'cannot pull the prompt {settings.langsmith_prompt_name}\n' + '\n'.join(errors))


def _assert_above_threshold(answers: list[tuple[str, str, str]], failures: list[str]) -> None:
    accuracy = 1 - len(failures) / len(answers)
    report = '\n'.join(failures)
    assert accuracy >= _ACCURACY_THRESHOLD, (
        f'accuracy {accuracy:.0%} over {len(answers)} conclusive '
        f'below {_ACCURACY_THRESHOLD:.0%}\n{report}'
    )


def _data(text: str, case: int) -> CommandData:
    return CommandData(text=text, jid=f'eval-{case}@g.us', sender_jid='eval@s.whatsapp.net')
