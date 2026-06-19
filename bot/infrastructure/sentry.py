"""Sentry initialization."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.types import Event, Hint

from bot.data.sentry_noise import (
    ABSORBED_EXCEPTION_NAMES,
    BROKER_REFUSAL_EXCEPTION_NAME,
    BROKER_REFUSAL_MARKER,
)


def init_sentry(dsn: str | None = None) -> None:
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=0.1,
            integrations=[FastApiIntegration()],
            before_send=_drop_expected_noise,
        )


def _drop_expected_noise(event: Event, hint: Hint) -> Event | None:
    if _is_absorbed_provider_error(hint):
        return None
    if _is_transient_broker_refusal(event, hint):
        return None
    return event


def _is_absorbed_provider_error(hint: Hint) -> bool:
    exception = hint.get('exc_info')
    if not exception:
        return False
    return exception[0].__name__ in ABSORBED_EXCEPTION_NAMES


def _is_transient_broker_refusal(event: Event, hint: Hint) -> bool:
    text = _event_text(event, hint)
    return BROKER_REFUSAL_EXCEPTION_NAME in text and BROKER_REFUSAL_MARKER in text


def _event_text(event: Event, hint: Hint) -> str:
    exception = hint.get('exc_info')
    exception_text = f'{exception[0].__name__} {exception[1]}' if exception else ''
    log_entry = event.get('logentry') or {}
    message = log_entry.get('message') or event.get('message') or ''
    return f'{exception_text} {message}'
