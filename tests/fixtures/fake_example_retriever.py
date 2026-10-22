from dataclasses import replace

from bot.domain.models.retrieved_example import RetrievedExample


class FakeExampleRetriever:
    def __init__(self) -> None:
        self._examples: list[RetrievedExample] = []

    def index(self, text: str, command: str) -> None:
        self._examples.append(RetrievedExample(text=text, command=command))

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedExample]:
        scored = [
            replace(example, score=self._similarity(query, example.text))
            for example in self._examples
        ]
        relevant = sorted(
            (example for example in scored if example.score > 0),
            key=lambda example: -example.score,
        )
        return relevant[:top_k]

    # Jaccard over tokens stands in for embedding similarity: 1.0 only for identical text.
    @staticmethod
    def _similarity(query: str, text: str) -> float:
        query_tokens = set(query.lower().split())
        text_tokens = set(text.lower().split())
        return len(query_tokens & text_tokens) / len(query_tokens | text_tokens)
