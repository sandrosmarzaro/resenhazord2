from dataclasses import dataclass


@dataclass(frozen=True)
class GameInfo:
    name: str
    year: str
    genres: str
    platforms: str
    rating: str | None
    cover_url: str
