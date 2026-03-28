"""Sentry initialization."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration


def init_sentry(dsn: str | None = None) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            integrations=[FastApiIntegration()],
        )
