from dataclasses import dataclass, field

from bot.data.nsfw_tags import MINOR_TAG_TERMS


@dataclass(frozen=True)
class HentaiGallery:
    title: str
    japanese_title: str | None
    artists: list[str]
    groups: list[str]
    tags: list[str]
    gallery_type: str
    language: str
    pages: int
    date: str
    cover_url: str
    cover_headers: dict[str, str] = field(default_factory=dict)
    url: str = ''
    # Tags that aren't shown in the caption but still say what the gallery holds.
    hidden_tags: list[str] = field(default_factory=list)

    @property
    def may_depict_minors(self) -> bool:
        # Fails closed: a gallery with no tags can't be vouched for.
        if not self.tags:
            return True
        texts = [*self.tags, *self.hidden_tags, self.title, self.japanese_title or '']
        return any(term in text.lower() for text in texts for term in MINOR_TAG_TERMS)
