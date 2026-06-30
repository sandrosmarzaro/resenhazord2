"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Sentry
    sentry_dsn: str | None = None

    # MongoDB
    mongodb_uri: str = 'mongodb://localhost:27017/resenhazord2'
    mongodb_db_name: str = 'resenhazord2'

    # Postgres — per-group command config (core node only).
    # Injected from the environment (.env locally, compose in prod); empty until
    # set, so no connection string or credential lives in the source.
    database_url: str = ''

    # Redis
    redis_url: str | None = None

    # RabbitMQ
    rabbitmq_url: str = 'amqp://guest:guest@localhost:5672/'

    # Server
    host: str = '0.0.0.0'
    port: int = 8000
    debug: bool = False

    resenhazord2_jid: str = ''
    resenhazord2_lid: str = ''
    resenha_jid: str = ''
    discord_token: str = ''
    discord_server_guild_id: str = ''
    discord_drive_guild_id: str = ''
    discord_app_id: str = ''
    telegram_token: str = ''
    telegram_bot_username: str = ''
    telegram_nsfw_chat_ids: str = ''

    nhentai_mirror_url: str = 'https://nhentai.to'

    # yt-dlp cookies file (Netscape format) for login-gated sources (Instagram, etc.).
    # Empty = no auth; path is in-container, mounted as a secret on the core node.
    ytdlp_cookies: str = ''

    bnet_id: str = ''
    bnet_secret: str = ''
    biblia_token: str = ''
    tmdb_api_key: str = ''
    omdb_api_key: str = ''
    jamendo_client_id: str = ''
    twitch_client_id: str = ''
    twitch_client_secret: str = ''
    rawg_api_key: str = ''
    restcountries_api_key: str = ''

    # OP.GG MCP
    opgg_mcp_url: str = 'https://mcp-api.op.gg/mcp'

    # LLM Providers (fallback order: github, mistral, groq)
    github_token: str = ''
    mistral_api_key: str = ''
    groq_api_key: str = ''
    # Route the agent's LLM calls through LangChain instead of the httpx ProviderChain
    llm_use_langchain: bool = False
    # Wrap the agent in the LangGraph stateful orchestrator (multi-turn conversation)
    agent_use_graph: bool = False

    # Upstash Vector (RAG few-shot example retrieval)
    upstash_vector_rest_url: str = ''
    upstash_vector_rest_token: str = ''

    model_config = {'env_file': '.env', 'extra': 'ignore'}
