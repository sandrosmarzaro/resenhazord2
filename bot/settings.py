"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Sentry
    sentry_dsn: str | None = None

    # MongoDB
    mongodb_uri: str = 'mongodb://localhost:27017/resenhazord2'
    mongodb_db_name: str = 'resenhazord2'

    # Redis
    redis_url: str | None = None

    # Server
    host: str = '0.0.0.0'
    port: int = 8000
    debug: bool = False

    resenhazord2_jid: str = ''
    resenha_jid: str = ''
    discord_token: str = ''
    discord_server_guild_id: str = ''
    discord_drive_guild_id: str = ''
    discord_app_id: str = ''
    telegram_token: str = ''
    telegram_bot_username: str = ''
    telegram_nsfw_chat_ids: str = ''

    nhentai_mirror_url: str = 'https://nhentai.to'

    bnet_id: str = ''
    bnet_secret: str = ''
    biblia_token: str = ''
    tmdb_api_key: str = ''
    omdb_api_key: str = ''
    jamendo_client_id: str = ''
    twitch_client_id: str = ''
    twitch_client_secret: str = ''
    rawg_api_key: str = ''

    # OP.GG MCP
    opgg_mcp_url: str = 'https://mcp-api.op.gg/mcp'

    # LLM Providers (fallback order: github, mistral, groq, google)
    github_token: str = ''
    mistral_api_key: str = ''
    groq_api_key: str = ''

    model_config = {'env_file': '.env', 'extra': 'ignore'}
