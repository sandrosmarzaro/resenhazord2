"""Build the example bank and upsert it to Upstash Vector.

Run once after changing commands or the hand-authored examples:

    uv run task index:examples
"""

import asyncio

from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import register_all_commands
from bot.infrastructure.llm.example_bank import build_example_bank
from bot.infrastructure.llm.upstash_retriever import UpstashExampleRetriever
from bot.settings import Settings


async def index_example_bank(settings: Settings) -> None:
    register_all_commands(settings)
    bank = build_example_bank(CommandRegistry.instance())
    retriever = UpstashExampleRetriever.from_credentials(
        settings.upstash_vector_rest_url, settings.upstash_vector_rest_token
    )
    await retriever.index_examples(bank)


if __name__ == '__main__':
    settings = Settings()
    if not settings.upstash_vector_rest_url:
        message = 'UPSTASH_VECTOR_REST_URL is not set; cannot index the example bank'
        raise SystemExit(message)
    asyncio.run(index_example_bank(settings))
