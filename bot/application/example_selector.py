from operator import attrgetter
from typing import ClassVar

import httpx
import structlog

from bot.data.agent_examples import AGENT_EXAMPLES
from bot.domain.constants import BOT_MENTION_TAG, MAX_USER_INPUT_LENGTH
from bot.domain.models.command_data import CommandData
from bot.domain.models.retrieved_example import RetrievedExample
from bot.ports.example_retriever_port import ExampleRetrieverPort

logger = structlog.get_logger()


class ExampleSelector:
    MAX_EXAMPLES: ClassVar[int] = 5
    # Upstash scores unrelated text at 0.68-0.72 and real paraphrases above 0.78.
    MIN_SIMILARITY: ClassVar[float] = 0.75
    # Only near-identical text: 'time do vasco' scores 0.80 against ',time corinthians'.
    DIRECT_MATCH_SIMILARITY: ClassVar[float] = 0.97

    def __init__(self, retriever: ExampleRetrieverPort | None) -> None:
        self._retriever = retriever

    async def select(self, user_input: str) -> list[RetrievedExample]:
        if self._retriever is None:
            return self._static_examples()

        query = user_input.replace(BOT_MENTION_TAG, '').strip()[:MAX_USER_INPUT_LENGTH]
        try:
            retrieved = await self._retriever.retrieve(query, self.MAX_EXAMPLES)
        except httpx.HTTPError as error:
            logger.warning('agent_retrieval_failed', error=str(error))
            return self._static_examples()
        return [example for example in retrieved if example.score >= self.MIN_SIMILARITY]

    def direct_match(
        self, data: CommandData, examples: list[RetrievedExample]
    ) -> RetrievedExample | None:
        # A reply to the bot's question means something only next to that question.
        if data.quoted_text:
            return None
        best = max(examples, key=attrgetter('score'), default=None)
        if best is None or best.score < self.DIRECT_MATCH_SIMILARITY:
            return None
        return best

    @classmethod
    def _static_examples(cls) -> list[RetrievedExample]:
        return [
            RetrievedExample(text=text, command=command)
            for text, command in AGENT_EXAMPLES[: cls.MAX_EXAMPLES]
        ]
