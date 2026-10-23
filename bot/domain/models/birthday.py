from dataclasses import dataclass


@dataclass(frozen=True)
class Birthday:
    user_jid: str
    day: int
    month: int
