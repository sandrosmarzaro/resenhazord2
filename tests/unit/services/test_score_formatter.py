from datetime import UTC, datetime

import pytest

from bot.domain.services.score_formatter import is_within_upcoming_window

_UPCOMING_WINDOW_HOURS = 6


@pytest.fixture
def evening_in_brazil(mocker):
    instant = datetime(2026, 10, 24, 23, 0, tzinfo=UTC)
    clock = mocker.patch('bot.domain.services.score_formatter.datetime', wraps=datetime)
    clock.now.side_effect = instant.astimezone


class TestUpcomingWindow:
    @pytest.mark.usefixtures('evening_in_brazil')
    def test_kickoff_later_tonight_in_brazilian_time_is_upcoming(self):
        assert is_within_upcoming_window('21:30', _UPCOMING_WINDOW_HOURS) is True

    @pytest.mark.usefixtures('evening_in_brazil')
    def test_kickoff_tomorrow_afternoon_is_outside_the_window(self):
        assert is_within_upcoming_window('16:00', _UPCOMING_WINDOW_HOURS) is False
