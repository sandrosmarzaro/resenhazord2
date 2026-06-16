from bot.domain.models.retrieved_example import RetrievedExample


class FakeExampleRetriever:
    def __init__(self) -> None:
        self._examples: list[RetrievedExample] = []

    def index(self, text: str, command: str) -> None:
        self._examples.append(RetrievedExample(text=text, command=command))

    async def retrieve(self, query: str, top_k: int) -> list[RetrievedExample]:
        scored = [
            (self._overlap(query, example.text), index, example)
            for index, example in enumerate(self._examples)
        ]
        relevant = sorted(
            (entry for entry in scored if entry[0] > 0),
            key=lambda entry: (-entry[0], entry[1]),
        )
        return [example for _, _, example in relevant[:top_k]]

    @staticmethod
    def _overlap(query: str, text: str) -> int:
        query_tokens = set(query.lower().split())
        text_tokens = set(text.lower().split())
        return len(query_tokens & text_tokens)
