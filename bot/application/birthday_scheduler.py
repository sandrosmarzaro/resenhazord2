import asyncio
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import ClassVar

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from bot.adapters.whatsapp.port import WhatsAppPort
from bot.data.birthday_messages import BIRTHDAY_GREETING, DEFAULT_BIRTHDAY_MESSAGE
from bot.domain.jid import strip_jid
from bot.domain.services.birthday_calendar import BirthdayCalendar

logger = structlog.get_logger()


class BirthdayScheduler:
    """Greets each chat's birthdays when the day turns in Brasília."""

    # Outlives the day, so a restart right after midnight still sees the greeting.
    SENT_RETENTION_SECONDS: ClassVar[int] = 2 * 86_400
    _KEY_PREFIX: ClassVar[str] = 'birthday_sent'

    def __init__(
        self,
        whatsapp: WhatsAppPort,
        redis: Redis | None,
        birthday_calendar: BirthdayCalendar | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._whatsapp = whatsapp
        self._redis = redis
        self._calendar = birthday_calendar or BirthdayCalendar()
        self._clock = clock or (lambda: datetime.now(BirthdayCalendar.TIMEZONE))

    async def run(self) -> None:
        # Celebrating on start covers a midnight the core was down for; the
        # once-a-day claim keeps a later restart from greeting twice.
        while True:
            try:
                await self.celebrate(self._clock().date())
            except Exception:
                logger.exception('birthday_celebration_error')
            await asyncio.sleep(self._seconds_until_midnight())

    async def celebrate(self, today: date) -> None:
        for chat_jid, user_jids in (await self._calendar.on(today)).items():
            if not await self._claim(chat_jid, today):
                continue
            text = await self._calendar.message_for(chat_jid) or DEFAULT_BIRTHDAY_MESSAGE
            mentions = ' '.join(f'@{strip_jid(jid)}' for jid in user_jids)
            greeting = BIRTHDAY_GREETING.format(mentions=mentions, text=text)
            await self._whatsapp.send_message(chat_jid, {'text': greeting, 'mentions': user_jids})

    async def _claim(self, chat_jid: str, today: date) -> bool:
        if self._redis is None:
            return True
        key = f'{self._KEY_PREFIX}:{chat_jid}:{today.isoformat()}'
        try:
            return bool(await self._redis.set(key, 1, nx=True, ex=self.SENT_RETENTION_SECONDS))
        except RedisError as error:
            # A duplicate greeting beats a missed birthday: fail open.
            logger.warning('birthday_claim_unavailable', error=str(error))
            return True

    def _seconds_until_midnight(self) -> float:
        now = self._clock()
        midnight = datetime.combine(now.date() + timedelta(days=1), time(), now.tzinfo)
        return (midnight - now).total_seconds()
