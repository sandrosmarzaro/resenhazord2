from datetime import date

import pytest

from bot.domain.commands.birthday import BirthdayCommand
from bot.domain.models.birthday import Birthday
from bot.domain.services.birthday_book import BirthdayBook
from bot.domain.services.birthday_calendar import BirthdayCalendar
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

SENDER = '5511999990000@s.whatsapp.net'
ALICE = '5511999990001@s.whatsapp.net'
BOB = '123456789012345@lid'


@pytest.fixture
def book(mocker):
    return mocker.AsyncMock(spec=BirthdayBook)


@pytest.fixture
def birthday_calendar(mocker):
    return mocker.AsyncMock(spec=BirthdayCalendar)


@pytest.fixture
def command(book, birthday_calendar):
    return BirthdayCommand(book, birthday_calendar, today=lambda: date(2026, 10, 23))


def _group(text: str, **kwargs):
    return GroupCommandDataFactory.build(text=text, sender_jid=SENDER, **kwargs)


class TestMatches:
    @pytest.mark.parametrize(
        'text', [',niver', ',aniversario', ',aniversário', ',birthday', ', NIVER 21/02']
    )
    def test_matches_every_alias(self, command, text):
        assert command.matches(text) is True

    def test_ignores_text_without_the_prefix(self, command):
        assert command.matches('niver') is False


class TestGroupOnly:
    @pytest.mark.anyio
    async def test_rejects_private_chat(self, command):
        messages = await command.run(PrivateCommandDataFactory.build(text=',niver 21/02'))

        assert 'só funciona em grupo' in messages[0].content.text


class TestRegisterSelf:
    @pytest.mark.anyio
    async def test_registers_the_sender(self, command, book):
        data = _group(',niver 21/02')

        await command.run(data)

        book.register.assert_awaited_once_with(data.jid, [Birthday(SENDER, day=21, month=2)])

    @pytest.mark.anyio
    async def test_rejects_an_impossible_date(self, command, book):
        messages = await command.run(_group(',niver 31/02'))

        book.register.assert_not_awaited()
        assert '31/02' in messages[0].content.text

    @pytest.mark.anyio
    async def test_rejects_text_that_is_not_a_date(self, command, book):
        messages = await command.run(_group(',niver amanhã'))

        book.register.assert_not_awaited()
        assert ',niver 21/02' in messages[0].content.text


class TestRegisterMentioned:
    @pytest.mark.anyio
    async def test_pairs_each_mention_with_its_date(self, command, book):
        data = _group(
            ',niver @5511999990001 01/12 @123456789012345 1/11', mentioned_jids=[ALICE, BOB]
        )

        messages = await command.run(data)

        book.register.assert_awaited_once_with(
            data.jid, [Birthday(ALICE, day=1, month=12), Birthday(BOB, day=1, month=11)]
        )
        assert messages[0].content.mentions == [ALICE, BOB]

    @pytest.mark.anyio
    async def test_rejects_a_mention_without_a_date(self, command, book):
        data = _group(',niver @5511999990001 01/12 @123456789012345', mentioned_jids=[ALICE, BOB])

        messages = await command.run(data)

        book.register.assert_not_awaited()
        assert '@fulano 01/12' in messages[0].content.text

    @pytest.mark.anyio
    async def test_rejects_an_impossible_date_for_a_mention(self, command, book):
        data = _group(',niver @5511999990001 32/12', mentioned_jids=[ALICE])

        messages = await command.run(data)

        book.register.assert_not_awaited()
        assert '32/12' in messages[0].content.text


class TestList:
    @pytest.mark.anyio
    async def test_lists_from_the_next_birthday_on(self, command, birthday_calendar):
        birthday_calendar.of_chat.return_value = [
            Birthday(ALICE, day=1, month=1),
            Birthday(BOB, day=1, month=12),
            Birthday(SENDER, day=23, month=10),
        ]

        messages = await command.run(_group(',niver'))

        text = messages[0].content.text
        assert text.index('23/10') < text.index('01/12') < text.index('01/01')
        assert messages[0].content.mentions == [SENDER, BOB, ALICE]

    @pytest.mark.anyio
    async def test_says_when_nobody_registered(self, command, birthday_calendar):
        birthday_calendar.of_chat.return_value = []

        messages = await command.run(_group(',niver'))

        assert 'Ninguém' in messages[0].content.text


class TestSave:
    @pytest.mark.anyio
    async def test_saves_the_quoted_text(self, command, book):
        data = _group(',niver save', quoted_text='feliz aniversário cara')

        await command.run(data)

        book.save_message.assert_awaited_once_with(data.jid, 'feliz aniversário cara')

    @pytest.mark.anyio
    async def test_requires_a_quote(self, command, book):
        messages = await command.run(_group(',niver save'))

        book.save_message.assert_not_awaited()
        assert 'Responda' in messages[0].content.text


class TestRemove:
    @pytest.mark.anyio
    async def test_removes_the_sender(self, command, book):
        book.remove.return_value = 1
        data = _group(',niver remove')

        await command.run(data)

        book.remove.assert_awaited_once_with(data.jid, [SENDER])

    @pytest.mark.anyio
    async def test_removes_the_mentioned(self, command, book):
        book.remove.return_value = 2
        data = _group(',niver remove @5511999990001 @123456789012345', mentioned_jids=[ALICE, BOB])

        messages = await command.run(data)

        book.remove.assert_awaited_once_with(data.jid, [ALICE, BOB])
        assert 'removido' in messages[0].content.text

    @pytest.mark.anyio
    async def test_says_when_there_was_nothing_to_remove(self, command, book):
        book.remove.return_value = 0

        messages = await command.run(_group(',niver remove'))

        assert 'Não achei' in messages[0].content.text
