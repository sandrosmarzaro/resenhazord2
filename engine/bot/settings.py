"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Sentry
    sentry_dsn: str | None = None

    # MongoDB
    mongodb_uri: str = 'mongodb://localhost:27017/resenhazord2'

    # Redis
    redis_url: str | None = None

    # Server
    host: str = '0.0.0.0'
    port: int = 8000
    debug: bool = False

    bnet_id: str = ''
    bnet_secret: str = ''
    biblia_token: str = ''
    tmdb_api_key: str = ''
    jamendo_client_id: str = ''
    twitch_client_id: str = ''
    twitch_client_secret: str = ''
    rawg_api_key: str = ''

    model_config = {'env_file': '.env', 'extra': 'ignore'}
