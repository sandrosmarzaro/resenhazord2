from datetime import date

import pytest
from testcontainers.mongodb import MongoDbContainer

from bot.domain.models.birthday import Birthday
from bot.domain.services.birthday_book import BirthdayBook
from bot.domain.services.birthday_calendar import BirthdayCalendar
from bot.infrastructure.mongodb import MongoDBConnection

CHAT_JID = '120363044041082732@g.us'
OTHER_CHAT_JID = '120363000000000000@g.us'
ALICE = '5511999990001@s.whatsapp.net'
BOB = '5511999990002@s.whatsapp.net'


@pytest.fixture(scope='module')
def mongo_uri():
    with MongoDbContainer('mongo:7') as container:
        yield container.get_connection_url()


@pytest.fixture
async def mongo(mongo_uri):
    MongoDBConnection.reset()
    MongoDBConnection.configure(mongo_uri, db_name='birthday_store_test')
    await MongoDBConnection.client().drop_database('birthday_store_test')
    yield
    await MongoDBConnection.close()


class TestRegister:
    @pytest.mark.anyio
    async def test_lists_the_registered_birthdays_of_the_chat(self, mongo):
        await BirthdayBook().register(
            CHAT_JID, [Birthday(ALICE, day=21, month=2), Birthday(BOB, day=1, month=12)]
        )
        await BirthdayBook().register(OTHER_CHAT_JID, [Birthday(BOB, day=5, month=5)])

        birthdays = await BirthdayCalendar().of_chat(CHAT_JID)

        assert sorted(birthdays, key=lambda birthday: birthday.user_jid) == [
            Birthday(ALICE, day=21, month=2),
            Birthday(BOB, day=1, month=12),
        ]

    @pytest.mark.anyio
    async def test_registering_again_replaces_the_date(self, mongo):
        await BirthdayBook().register(CHAT_JID, [Birthday(ALICE, day=21, month=2)])
        await BirthdayBook().register(CHAT_JID, [Birthday(ALICE, day=22, month=3)])

        birthdays = await BirthdayCalendar().of_chat(CHAT_JID)

        assert birthdays == [Birthday(ALICE, day=22, month=3)]

    @pytest.mark.anyio
    async def test_drops_the_device_suffix(self, mongo):
        await BirthdayBook().register(
            CHAT_JID, [Birthday('5511999990001:3@s.whatsapp.net', day=21, month=2)]
        )

        birthdays = await BirthdayCalendar().of_chat(CHAT_JID)

        assert birthdays == [Birthday(ALICE, day=21, month=2)]


class TestRemove:
    @pytest.mark.anyio
    async def test_removes_only_the_given_people(self, mongo):
        await BirthdayBook().register(
            CHAT_JID, [Birthday(ALICE, day=21, month=2), Birthday(BOB, day=1, month=12)]
        )

        removed = await BirthdayBook().remove(CHAT_JID, [ALICE])

        assert removed == 1
        assert await BirthdayCalendar().of_chat(CHAT_JID) == [Birthday(BOB, day=1, month=12)]


class TestOn:
    @pytest.mark.anyio
    async def test_groups_the_celebrants_by_chat(self, mongo):
        await BirthdayBook().register(
            CHAT_JID, [Birthday(ALICE, day=21, month=2), Birthday(BOB, day=21, month=2)]
        )
        await BirthdayBook().register(OTHER_CHAT_JID, [Birthday(BOB, day=21, month=2)])
        await BirthdayBook().register(OTHER_CHAT_JID, [Birthday(ALICE, day=1, month=12)])

        celebrants = await BirthdayCalendar().on(date(2027, 2, 21))

        assert {chat: sorted(jids) for chat, jids in celebrants.items()} == {
            CHAT_JID: [ALICE, BOB],
            OTHER_CHAT_JID: [BOB],
        }

    @pytest.mark.anyio
    async def test_leap_day_birthdays_fall_on_february_28_in_common_years(self, mongo):
        await BirthdayBook().register(CHAT_JID, [Birthday(ALICE, day=29, month=2)])

        celebrants = await BirthdayCalendar().on(date(2027, 2, 28))

        assert celebrants == {CHAT_JID: [ALICE]}

    @pytest.mark.anyio
    async def test_leap_day_birthdays_wait_for_february_29_in_leap_years(self, mongo):
        await BirthdayBook().register(CHAT_JID, [Birthday(ALICE, day=29, month=2)])

        celebrants = await BirthdayCalendar().on(date(2028, 2, 28))

        assert celebrants == {}


class TestMessage:
    @pytest.mark.anyio
    async def test_returns_the_saved_text(self, mongo):
        await BirthdayBook().save_message(CHAT_JID, 'primeira versão')
        await BirthdayBook().save_message(CHAT_JID, 'feliz aniversário cara')

        text = await BirthdayCalendar().message_for(CHAT_JID)

        assert text == 'feliz aniversário cara'

    @pytest.mark.anyio
    async def test_returns_none_without_a_saved_text(self, mongo):
        text = await BirthdayCalendar().message_for(CHAT_JID)

        assert text is None
