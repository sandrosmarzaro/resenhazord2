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

    model_config = {'env_file': '.env', 'extra': 'ignore'}
