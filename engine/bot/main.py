"""FastAPI entry point — run with: uvicorn bot.main:app"""

from bot.adapters.http.app import app
from bot.infrastructure.sentry import init_observability
from bot.settings import Settings

settings = Settings()
init_observability(settings.sentry_dsn)

__all__ = ['app']
