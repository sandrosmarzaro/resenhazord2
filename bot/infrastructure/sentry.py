"""Sentry + structlog initialization."""

from __future__ import annotations

import sentry_sdk
import structlog
from sentry_sdk.integrations.fastapi import FastApiIntegration


def init_observability(dsn: str | None = None) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            integrations=[FastApiIntegration()],
        )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )
