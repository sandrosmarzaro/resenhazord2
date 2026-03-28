from dataclasses import dataclass, field


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
