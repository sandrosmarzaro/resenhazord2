from dataclasses import dataclass


@dataclass(frozen=True)
class YouTubeShort:
    url: str
    title: str
    channel: str
