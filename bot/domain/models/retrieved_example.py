from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedExample:
    text: str
    command: str
