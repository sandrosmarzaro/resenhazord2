from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    tool_call: dict | None = None
