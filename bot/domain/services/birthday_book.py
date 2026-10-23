from typing import ClassVar

from pymongo import UpdateOne

from bot.domain.jid import normalize_jid, normalize_jids
from bot.domain.models.birthday import Birthday
from bot.infrastructure.mongodb import MongoDBConnection


class BirthdayBook:
    """Writes each chat's birthdays and the text its members get on the day."""

    BIRTHDAYS: ClassVar[str] = 'birthdays'
    MESSAGES: ClassVar[str] = 'birthday_messages'

    async def register(self, chat_jid: str, birthdays: list[Birthday]) -> None:
        # The id pins one date per person per chat, so registering again replaces it.
        updates = [
            UpdateOne(
                {'_id': f'{chat_jid}:{normalize_jid(birthday.user_jid)}'},
                {
                    '$set': {
                        'chat_jid': chat_jid,
                        'user_jid': normalize_jid(birthday.user_jid),
                        'day': birthday.day,
                        'month': birthday.month,
                    }
                },
                upsert=True,
            )
            for birthday in birthdays
        ]
        await MongoDBConnection.collection(self.BIRTHDAYS).bulk_write(updates)

    async def remove(self, chat_jid: str, user_jids: list[str]) -> int:
        result = await MongoDBConnection.collection(self.BIRTHDAYS).delete_many(
            {'chat_jid': chat_jid, 'user_jid': {'$in': normalize_jids(user_jids)}}
        )
        return result.deleted_count

    async def save_message(self, chat_jid: str, text: str) -> None:
        await MongoDBConnection.collection(self.MESSAGES).update_one(
            {'_id': chat_jid}, {'$set': {'text': text}}, upsert=True
        )
