from dataclasses import dataclass, field

from bot.domain.jid import normalize_jid


@dataclass(frozen=True)
class RemovalTargets:
    """Who to remove from a mention list: by 1-based index or by @mention."""

    indices: list[int] = field(default_factory=list)
    mentioned: list[str] = field(default_factory=list)

    @property
    def is_self_exit(self) -> bool:
        return not self.indices and not self.mentioned

    def resolve(self, participants: list[str]) -> list[str]:
        by_index = [participants[i - 1] for i in self.indices if 0 < i <= len(participants)]
        wanted = {normalize_jid(jid) for jid in self.mentioned}
        by_mention = [p for p in participants if normalize_jid(p) in wanted]
        return by_index + by_mention
