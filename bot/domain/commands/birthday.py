import re
from collections.abc import Callable
from datetime import date, datetime
from typing import ClassVar

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import ArgType, Category, Command, CommandConfig, ParsedCommand
from bot.domain.jid import normalize_jid, strip_jid
from bot.domain.models.birthday import Birthday
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.birthday_book import BirthdayBook
from bot.domain.services.birthday_calendar import BirthdayCalendar


class InvalidBirthdayError(ValueError):
    """Raised when the command text holds no valid date for someone."""


class ImpossibleDateError(InvalidBirthdayError):
    def __init__(self, text: str) -> None:
        super().__init__(f'{text} não existe no calendário 🤨')


class BirthdayCommand(Command):
    DATE: ClassVar[re.Pattern[str]] = re.compile(r'(\d{1,2})/(\d{1,2})')
    MENTION_WITH_DATE: ClassVar[re.Pattern[str]] = re.compile(r'@(\d+)\s+(\d{1,2}/\d{1,2})')
    # A leap year accepts 29/02 when validating a date that has no year.
    LEAP_YEAR: ClassVar[int] = 2000
    USAGE: ClassVar[str] = 'Manda assim: *,niver 21/02* ou *,niver @fulano 01/12* 🤔'

    def __init__(
        self,
        book: BirthdayBook | None = None,
        birthday_calendar: BirthdayCalendar | None = None,
        today: Callable[[], date] | None = None,
    ) -> None:
        super().__init__()
        self._book = book or BirthdayBook()
        self._calendar = birthday_calendar or BirthdayCalendar()
        self._today = today or (lambda: datetime.now(BirthdayCalendar.TIMEZONE).date())

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='niver',
            aliases=['aniversario', 'aniversário', 'birthday'],
            args=ArgType.OPTIONAL,
            args_label='data',
            group_only=True,
            category=Category.GROUP,
        )

    @property
    def menu_description(self) -> str:
        return (
            'Cadastra aniversários e parabeniza à meia-noite. *,niver 21/02*, '
            '*,niver @fulano 01/12*, *,niver* lista, *,niver remove* e *,niver save* no quote.'
        )

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        rest = parsed.rest.strip()
        keyword = rest.split(' ', 1)[0].lower()
        if keyword == 'save':
            return await self._save(data)
        if keyword == 'remove':
            return await self._remove(data)
        if not rest:
            return await self._list(data)
        try:
            birthdays = self._parse(data, rest)
        except InvalidBirthdayError as error:
            return [Reply.to(data).text(str(error))]
        await self._book.register(data.jid, birthdays)
        lines = [f'- @{strip_jid(b.user_jid)} {self._format(b)}' for b in birthdays]
        mentions = [birthday.user_jid for birthday in birthdays]
        return [Reply.to(data).text_with('🎂 Anotado!\n\n' + '\n'.join(lines), mentions)]

    def _parse(self, data: CommandData, rest: str) -> list[Birthday]:
        if not data.mentioned_jids:
            if not self.DATE.fullmatch(rest):
                raise InvalidBirthdayError(self.USAGE)
            return [self._birthday(data.sender_jid, rest)]
        dates = dict(self.MENTION_WITH_DATE.findall(rest))
        by_number = {strip_jid(normalize_jid(jid)): jid for jid in data.mentioned_jids}
        if dates.keys() != by_number.keys():
            raise InvalidBirthdayError(self.USAGE)
        return [self._birthday(by_number[number], text) for number, text in dates.items()]

    def _birthday(self, user_jid: str, text: str) -> Birthday:
        day, month = (int(part) for part in text.split('/'))
        try:
            date(self.LEAP_YEAR, month, day)
        except ValueError as error:
            raise ImpossibleDateError(text) from error
        return Birthday(user_jid, day=day, month=month)

    async def _list(self, data: CommandData) -> list[BotMessage]:
        birthdays = await self._calendar.of_chat(data.jid)
        if not birthdays:
            return [Reply.to(data).text('Ninguém cadastrou aniversário ainda 🎈')]
        today = self._today()
        upcoming = sorted(
            birthdays,
            key=lambda b: ((b.month, b.day) < (today.month, today.day), b.month, b.day),
        )
        lines = [f'- {self._format(b)} @{strip_jid(b.user_jid)}' for b in upcoming]
        mentions = [birthday.user_jid for birthday in upcoming]
        return [Reply.to(data).text_with('🎂 *ANIVERSÁRIOS* 🎂\n\n' + '\n'.join(lines), mentions)]

    async def _save(self, data: CommandData) -> list[BotMessage]:
        if not data.quoted_text:
            return [Reply.to(data).text('Responda a mensagem de parabéns com *,niver save* 🤔')]
        await self._book.save_message(data.jid, data.quoted_text)
        return [Reply.to(data).text('Mensagem de aniversário salva! 🎂')]

    async def _remove(self, data: CommandData) -> list[BotMessage]:
        targets = data.mentioned_jids or [data.sender_jid]
        if not await self._book.remove(data.jid, targets):
            return [Reply.to(data).text('Não achei esse aniversário 🤔')]
        return [Reply.to(data).text('Aniversário removido! 🗑️')]

    @staticmethod
    def _format(birthday: Birthday) -> str:
        return f'{birthday.day:02d}/{birthday.month:02d}'
