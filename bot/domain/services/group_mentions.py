"""Facade for group mention list operations — delegates to single-responsibility classes."""

from bot.domain.services.mentions.add_to_mention_list import AddToMentionList
from bot.domain.services.mentions.create_mention_list import CreateMentionList
from bot.domain.services.mentions.delete_mention_list import DeleteMentionList
from bot.domain.services.mentions.exit_mention_list import ExitMentionList
from bot.domain.services.mentions.get_mention_list import GetMentionList
from bot.domain.services.mentions.list_mention_lists import ListMentionLists
from bot.domain.services.mentions.mention_group import MentionGroup
from bot.domain.services.mentions.rename_mention_list import RenameMentionList


class GroupMentionsService:
    """Facade that delegates each operation to its dedicated class."""

    async def create(
        self,
        chat_jid: str,
        sender_jid: str,
        group_name: str,
        mentioned: list[str],
    ) -> dict:
        return await CreateMentionList().execute(chat_jid, sender_jid, group_name, mentioned)

    async def rename(self, chat_jid: str, old_name: str, new_name: str) -> dict:
        return await RenameMentionList().execute(chat_jid, old_name, new_name)

    async def delete(self, chat_jid: str, group_name: str) -> dict:
        return await DeleteMentionList().execute(chat_jid, group_name)

    async def list_all(self, chat_jid: str) -> dict:
        return await ListMentionLists().execute(chat_jid)

    async def list_one(self, chat_jid: str, group_name: str) -> dict:
        return await GetMentionList().execute(chat_jid, group_name)

    async def add(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        participants: list[str],
    ) -> dict:
        return await AddToMentionList().execute(chat_jid, group_name, sender_jid, participants)

    async def exit(
        self,
        chat_jid: str,
        group_name: str,
        sender_jid: str,
        indices: list[int],
    ) -> dict:
        return await ExitMentionList().execute(chat_jid, group_name, sender_jid, indices)

    async def mention(self, chat_jid: str, group_name: str) -> dict:
        return await MentionGroup().execute(chat_jid, group_name)
