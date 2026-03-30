from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    title: str
    author: str
    url: str
    stream_url: str
    duration: int
    thumbnail: str
    requested_by: str
    requested_by_id: int
