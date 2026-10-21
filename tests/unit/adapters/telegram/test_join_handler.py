from datetime import UTC, datetime

import pytest
from telegram import (
    Chat,
    ChatMemberAdministrator,
    ChatMemberBanned,
    ChatMemberLeft,
    ChatMemberMember,
    ChatMemberUpdated,
    Update,
    User,
)
from telegram.constants import ChatType

from bot.adapters.telegram.formatter import WhatsAppHtmlFormatter
from bot.adapters.telegram.join_handler import TelegramJoinHandler
from bot.data.welcome_messages import TELEGRAM_WELCOME
from bot.ports.telegram_port import TelegramKind, TelegramOutbound

GROUP_ID = -100123
BOT = User(id=42, first_name='Resenhazord', is_bot=True)
ADDER = User(id=7, first_name='Fulano', is_bot=False)
FAR_FUTURE = datetime(2100, 1, 1, tzinfo=UTC)


def _left():
    return ChatMemberLeft(user=BOT)


def _banned():
    return ChatMemberBanned(user=BOT, until_date=FAR_FUTURE)


def _member():
    return ChatMemberMember(user=BOT)


def _admin():
    return ChatMemberAdministrator(
        user=BOT,
        can_be_edited=False,
        is_anonymous=False,
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=True,
        can_restrict_members=True,
        can_promote_members=False,
        can_change_info=True,
        can_invite_users=True,
        can_post_stories=False,
        can_edit_stories=False,
        can_delete_stories=False,
    )


def _membership_update(old, new, *, chat_type=ChatType.SUPERGROUP):
    change = ChatMemberUpdated(
        chat=Chat(id=GROUP_ID, type=chat_type),
        from_user=ADDER,
        date=datetime.now(UTC),
        old_chat_member=old,
        new_chat_member=new,
    )
    return Update(update_id=1, my_chat_member=change)


class TestGreetsOnJoin:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('old', 'new'),
        [(_left, _member), (_left, _admin), (_banned, _member)],
        ids=['added', 'added-as-admin', 'unbanned-and-added'],
    )
    async def test_greets_the_group_the_bot_joined(self, port, old, new):
        await TelegramJoinHandler().handle(port, _membership_update(old(), new()))

        port.send.assert_awaited_once_with(
            TelegramOutbound(
                kind=TelegramKind.TEXT,
                chat_id=GROUP_ID,
                text=WhatsAppHtmlFormatter.to_html(TELEGRAM_WELCOME),
            )
        )

    def test_welcome_points_to_the_slash_menu(self):
        assert '/menu' in TELEGRAM_WELCOME


class TestStaysQuiet:
    @pytest.mark.anyio
    @pytest.mark.parametrize(
        ('old', 'new'),
        [(_member, _admin), (_member, _left), (_admin, _banned)],
        ids=['promoted', 'removed', 'banned'],
    )
    async def test_ignores_changes_that_are_not_a_join(self, port, old, new):
        await TelegramJoinHandler().handle(port, _membership_update(old(), new()))

        port.send.assert_not_awaited()

    @pytest.mark.anyio
    async def test_ignores_private_chats(self, port):
        update = _membership_update(_banned(), _member(), chat_type=ChatType.PRIVATE)

        await TelegramJoinHandler().handle(port, update)

        port.send.assert_not_awaited()

    @pytest.mark.anyio
    async def test_ignores_updates_without_a_membership_change(self, port):
        await TelegramJoinHandler().handle(port, Update(update_id=1))

        port.send.assert_not_awaited()
