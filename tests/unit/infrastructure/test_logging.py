import logging

from bot.infrastructure.logging import configure_logging


class TestHttpxRequestLines:
    def test_info_request_lines_are_suppressed(self):
        configure_logging()

        enabled = logging.getLogger('httpx').isEnabledFor(logging.INFO)

        assert enabled is False

    def test_warnings_still_pass(self):
        configure_logging()

        enabled = logging.getLogger('httpx').isEnabledFor(logging.WARNING)

        assert enabled is True
