import asyncio
from datetime import date, datetime

import pytest
from fakeredis.aioredis import FakeRedis
from redis.asyncio import Redis

from bot.application.birthday_scheduler import BirthdayScheduler
from bot.data.birthday_messages import DEFAULT_BIRTHDAY_MESSAGE
from bot.domain.services.birthday_calendar import BirthdayCalendar

CHAT_JID = '120363044041082732@g.us'
ALICE = '5511999990001@s.whatsapp.net'
BOB = '123456789012345@lid'
TODAY = date(2026, 2, 21)
LATE_EVENING = datetime(2026, 2, 21, 23, 0, tzinfo=BirthdayCalendar.TIMEZONE)
SECONDS_IN_AN_HOUR = 3600


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def birthday_calendar(mocker):
    birthday_calendar = mocker.AsyncMock(spec=BirthdayCalendar)
    birthday_calendar.on.return_value = {CHAT_JID: [ALICE, BOB]}
    birthday_calendar.message_for.return_value = 'feliz aniversário cara'
    return birthday_calendar


@pytest.fixture
def scheduler(mock_whatsapp, birthday_calendar):
    return BirthdayScheduler(mock_whatsapp, FakeRedis(), birthday_calendar, lambda: LATE_EVENING)


@pytest.fixture
def sleep(mocker):
    # The first sleep ends the loop, so a test sees exactly one iteration.
    return mocker.patch(
        'bot.application.birthday_scheduler.asyncio.sleep',
        new_callable=mocker.AsyncMock,
        side_effect=asyncio.CancelledError,
    )


class TestCelebrate:
    @pytest.mark.anyio
    async def test_mentions_the_celebrants_above_the_group_text(self, scheduler, mock_whatsapp):
        await scheduler.celebrate(TODAY)

        mock_whatsapp.send_message.assert_awaited_once_with(
            CHAT_JID,
            {
                'text': '🎂 @5511999990001 @123456789012345\n\nfeliz aniversário cara',
                'mentions': [ALICE, BOB],
            },
        )

    @pytest.mark.anyio
    async def test_falls_back_to_the_default_text(
        self, scheduler, birthday_calendar, mock_whatsapp
    ):
        birthday_calendar.message_for.return_value = None

        await scheduler.celebrate(TODAY)

        content = mock_whatsapp.send_message.await_args.args[1]
        assert content['text'].endswith(DEFAULT_BIRTHDAY_MESSAGE)

    @pytest.mark.anyio
    async def test_greets_each_chat_once_a_day(self, scheduler, mock_whatsapp):
        await scheduler.celebrate(TODAY)
        await scheduler.celebrate(TODAY)

        assert mock_whatsapp.send_message.await_count == 1

    @pytest.mark.anyio
    async def test_greets_again_on_another_day(self, scheduler, mock_whatsapp):
        await scheduler.celebrate(TODAY)
        await scheduler.celebrate(date(2027, 2, 21))

        assert mock_whatsapp.send_message.await_count == 2

    @pytest.mark.anyio
    async def test_greets_without_redis(self, mock_whatsapp, birthday_calendar):
        scheduler = BirthdayScheduler(mock_whatsapp, None, birthday_calendar)

        await scheduler.celebrate(TODAY)

        assert mock_whatsapp.send_message.await_count == 1

    @pytest.mark.anyio
    async def test_greets_when_redis_is_down(self, mock_whatsapp, birthday_calendar):
        redis = Redis.from_url('redis://127.0.0.1:1')
        scheduler = BirthdayScheduler(mock_whatsapp, redis, birthday_calendar)

        await scheduler.celebrate(TODAY)

        assert mock_whatsapp.send_message.await_count == 1


class TestRun:
    @pytest.mark.anyio
    async def test_celebrates_today_then_sleeps_until_midnight(
        self, scheduler, birthday_calendar, sleep
    ):
        with pytest.raises(asyncio.CancelledError):
            await scheduler.run()

        birthday_calendar.on.assert_awaited_once_with(TODAY)
        sleep.assert_awaited_once_with(SECONDS_IN_AN_HOUR)

    @pytest.mark.anyio
    async def test_a_failed_day_still_waits_for_the_next(self, scheduler, birthday_calendar, sleep):
        birthday_calendar.on.side_effect = RuntimeError('mongo down')

        with pytest.raises(asyncio.CancelledError):
            await scheduler.run()

        sleep.assert_awaited_once_with(SECONDS_IN_AN_HOUR)
