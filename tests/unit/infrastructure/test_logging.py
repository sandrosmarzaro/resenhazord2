import logging

import pytest
import structlog

from bot.infrastructure.logging import configure_logging


# configure_logging turns on cache_logger_on_first_use with a stdlib factory. Left in
# place, every module logger first used later in the process binds to a stream pytest
# has closed, and capture_logs or any reconfiguration never reaches it again.
@pytest.fixture(autouse=True)
def _restore_structlog():
    yield
    structlog.reset_defaults()


class TestHttpxRequestLines:
    def test_info_request_lines_are_suppressed(self):
        configure_logging()

        enabled = logging.getLogger('httpx').isEnabledFor(logging.INFO)

        assert enabled is False

    def test_warnings_still_pass(self):
        configure_logging()

        enabled = logging.getLogger('httpx').isEnabledFor(logging.WARNING)

        assert enabled is True
