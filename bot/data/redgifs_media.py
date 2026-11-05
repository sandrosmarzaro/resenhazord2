from dataclasses import dataclass


@dataclass(frozen=True)
class RedGifsMedia:
    url: str
    is_video: bool
