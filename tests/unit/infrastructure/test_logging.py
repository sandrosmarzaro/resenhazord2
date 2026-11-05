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


class TestUpstreamFailures:
    def test_an_upstream_failed_log_counts_a_failure_of_that_upstream(self, mocker):
        failures = mocker.patch('bot.infrastructure.metrics._upstream_failures')
        configure_logging()

        structlog.get_logger().warning('upstream_failed', upstream='espn')

        failures.add.assert_called_once_with(1, {'upstream': 'espn'})

    def test_other_events_count_nothing(self, mocker):
        failures = mocker.patch('bot.infrastructure.metrics._upstream_failures')
        configure_logging()

        structlog.get_logger().warning('command_unexpected_error', upstream='espn')

        failures.add.assert_not_called()
