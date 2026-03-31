"""Unified logging — routes all logs (including uvicorn) through structlog.

Inspired by https://github.com/polarsource/polar/blob/main/server/polar/logging.py
"""

import logging
import logging.config
import os

import structlog


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /health' not in record.getMessage()


_timestamper = structlog.processors.TimeStamper(fmt='iso')

_shared_processors: list = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.PositionalArgumentsFormatter(),
    _timestamper,
    structlog.processors.UnicodeDecoder(),
    structlog.processors.StackInfoRenderer(),
]


def configure_logging() -> None:
    """Configure structlog and stdlib logging with unified formatting."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_format = os.environ.get('LOG_FORMAT', 'console').lower()

    renderer: structlog.types.Processor
    if log_format == 'json':
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    logging.config.dictConfig(
        {
            'version': 1,
            'disable_existing_loggers': False,
            'filters': {
                'health_check': {
                    '()': HealthCheckFilter,
                },
            },
            'formatters': {
                'structlog': {
                    '()': structlog.stdlib.ProcessorFormatter,
                    'processors': [
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        renderer,
                    ],
                    'foreign_pre_chain': _shared_processors,
                },
            },
            'handlers': {
                'default': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'structlog',
                    'filters': ['health_check'],
                },
            },
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': log_level,
                    'propagate': False,
                },
                **{
                    name: {'handlers': [], 'propagate': True}
                    for name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']
                },
            },
        }
    )

    structlog.configure(
        processors=[
            *_shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
