"""FastAPI entry point — run with: uvicorn bot.main:app"""

from bot.adapters.http.app import app
from bot.infrastructure.logging import configure_logging
from bot.infrastructure.otel import init_otel
from bot.infrastructure.sentry import init_sentry
from bot.settings import Settings

settings = Settings()
configure_logging()
init_sentry(settings.sentry_dsn)
init_otel(settings)

__all__ = ['app']
