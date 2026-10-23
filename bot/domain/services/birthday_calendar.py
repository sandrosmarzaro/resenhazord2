import calendar
from collections import defaultdict
from datetime import date
from typing import ClassVar
from zoneinfo import ZoneInfo

from bot.domain.models.birthday import Birthday
from bot.domain.services.birthday_book import BirthdayBook
from bot.infrastructure.mongodb import MongoDBConnection


class BirthdayCalendar:
    """Reads what BirthdayBook wrote: who celebrates when, and with which text."""

    # The groups are Brazilian, so the day turns at midnight in Brasília.
    TIMEZONE: ClassVar[ZoneInfo] = ZoneInfo('America/Sao_Paulo')
    LEAP_DAY: ClassVar[tuple[int, int]] = (29, 2)
    LAST_DAY_OF_FEBRUARY: ClassVar[tuple[int, int]] = (28, 2)

    async def of_chat(self, chat_jid: str) -> list[Birthday]:
        cursor = MongoDBConnection.collection(BirthdayBook.BIRTHDAYS).find({'chat_jid': chat_jid})
        return [self._to_birthday(document) async for document in cursor]

    async def on(self, today: date) -> dict[str, list[str]]:
        dates = [{'day': day, 'month': month} for day, month in self._dates_celebrated(today)]
        cursor = MongoDBConnection.collection(BirthdayBook.BIRTHDAYS).find({'$or': dates})
        celebrants: defaultdict[str, list[str]] = defaultdict(list)
        async for document in cursor:
            celebrants[document['chat_jid']].append(document['user_jid'])
        return dict(celebrants)

    async def message_for(self, chat_jid: str) -> str | None:
        document = await MongoDBConnection.collection(BirthdayBook.MESSAGES).find_one(
            {'_id': chat_jid}
        )
        return document['text'] if document else None

    @classmethod
    def _dates_celebrated(cls, today: date) -> list[tuple[int, int]]:
        dates = [(today.day, today.month)]
        # Without a February 29, leap-day birthdays move to the 28th.
        if dates[0] == cls.LAST_DAY_OF_FEBRUARY and not calendar.isleap(today.year):
            dates.append(cls.LEAP_DAY)
        return dates

    @staticmethod
    def _to_birthday(document: dict) -> Birthday:
        return Birthday(document['user_jid'], day=document['day'], month=document['month'])
