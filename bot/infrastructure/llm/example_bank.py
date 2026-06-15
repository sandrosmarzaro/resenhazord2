from typing import ClassVar

from bot.application.command_registry import CommandRegistry
from bot.data.agent_examples import AGENT_EXAMPLES
from bot.domain.commands.base import Command, CommandScope
from bot.domain.models.retrieved_example import RetrievedExample


class _BankBuilder:
    EXCLUDED_SCOPES: ClassVar[frozenset[CommandScope]] = frozenset(
        {CommandScope.NSFW, CommandScope.DISABLED}
    )

    @classmethod
    def is_included(cls, command: Command) -> bool:
        return command.config.scope not in cls.EXCLUDED_SCOPES

    @classmethod
    def baseline_for(cls, command: Command) -> list[RetrievedExample]:
        config = command.config
        target = f',{config.name}'
        phrasings = [config.name, *config.aliases]
        if command.menu_description:
            phrasings.append(command.menu_description)
        return [RetrievedExample(text=phrasing, command=target) for phrasing in phrasings]


def build_example_bank(
    registry: CommandRegistry,
    hand_examples: list[tuple[str, str]] | None = None,
) -> list[RetrievedExample]:
    """Merge hand-authored slang examples with a generated per-command baseline.

    Hand examples come first so a curated phrasing wins over the generated
    baseline when both share the same text.
    """
    examples = AGENT_EXAMPLES if hand_examples is None else hand_examples

    bank: list[RetrievedExample] = []
    seen: set[str] = set()

    for text, target in examples:
        _dedup_add(bank, seen, RetrievedExample(text=text, command=target))

    for command in registry.get_all():
        if not _BankBuilder.is_included(command):
            continue
        for example in _BankBuilder.baseline_for(command):
            _dedup_add(bank, seen, example)

    return bank


def _dedup_add(bank: list[RetrievedExample], seen: set[str], example: RetrievedExample) -> None:
    key = example.text.strip().lower()
    if key in seen:
        return
    seen.add(key)
    bank.append(example)
