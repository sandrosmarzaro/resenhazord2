from collections.abc import Iterable

from bot.data.nsfw_tags import MINOR_TAG_TERMS
from bot.infrastructure.metrics import record_minors_drop


class MinorsFilter:
    """The one denylist check every NSFW source runs its labels through.

    Best effort: a substring of any term in any label flags the item. Each flag is
    counted by source, so the compliance view shows how much each feed hands back
    that the bot refuses to send.
    """

    @staticmethod
    def flags(source: str, labels: Iterable[str]) -> bool:
        flagged = any(term in label.lower() for label in labels for term in MINOR_TAG_TERMS)
        if flagged:
            record_minors_drop(source)
        return flagged
