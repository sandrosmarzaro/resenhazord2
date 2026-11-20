import pytest

from bot.application.member_blocks import MemberBlocks
from bot.domain.models.blocked_member import BlockedMember
from bot.domain.models.chat_config import ChatConfig, ChatKey, ChatType
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

PN = '5527900000003@s.whatsapp.net'
LID = '123456789012345@lid'
ADMIN_PN = '5527900000002@s.whatsapp.net'
GROUP = '120000000000000001@g.us'
NO_TARGET = '❓ Marque quem bloquear ou liberar: *,config bloquear @fulano*.'
UNSUPPORTED = '🚧 Por enquanto só dá pra bloquear membros em grupos do WhatsApp.'


@pytest.fixture
def store(mocker):
    store = mocker.AsyncMock()
    store.load.return_value = ChatConfig()
    return store


@pytest.fixture
def blocks(store):
    return MemberBlocks(store)


@pytest.fixture
def lid_group(mock_whatsapp):
    mock_whatsapp.group_metadata.return_value = {
        'participants': [
            {'id': LID, 'phoneNumber': PN, 'admin': None},
            {'id': '999@lid', 'phoneNumber': ADMIN_PN, 'admin': 'admin'},
        ]
    }
    return mock_whatsapp


def group_data(*mentioned: str):
    return GroupCommandDataFactory(platform='whatsapp', jid=GROUP, mentioned_jids=list(mentioned))


def group_key() -> ChatKey:
    return ChatKey(platform='whatsapp', native_id=GROUP, type=ChatType.GROUP)


class TestBlock:
    @pytest.mark.anyio
    async def test_a_lid_mention_stores_the_phone_number_too(self, blocks, store, lid_group):
        await blocks.apply(group_data(LID), 'bloquear', lid_group)

        store.block_members.assert_awaited_once_with(
            group_key(), [BlockedMember(key=PN, alt_key=LID)]
        )

    @pytest.mark.anyio
    async def test_a_phone_number_mention_stores_the_lid_too(self, blocks, store, lid_group):
        await blocks.apply(group_data(PN), 'bloquear', lid_group)

        store.block_members.assert_awaited_once_with(
            group_key(), [BlockedMember(key=PN, alt_key=LID)]
        )

    @pytest.mark.anyio
    async def test_a_member_missing_from_the_group_is_stored_as_mentioned(
        self, blocks, store, lid_group
    ):
        absent = '5527900000009@s.whatsapp.net'

        await blocks.apply(group_data(absent), 'bloquear', lid_group)

        store.block_members.assert_awaited_once_with(group_key(), [BlockedMember(key=absent)])

    @pytest.mark.anyio
    async def test_replies_mentioning_the_member(self, blocks, lid_group):
        reply = await blocks.apply(group_data(LID), 'bloquear', lid_group)

        assert reply.content.text == '🚫 @123456789012345 não pode mais usar o bot neste grupo.'
        assert reply.content.mentions == [LID]

    @pytest.mark.anyio
    async def test_refuses_an_admin_and_stores_nobody(self, blocks, store, lid_group):
        reply = await blocks.apply(group_data(PN, ADMIN_PN), 'bloquear', lid_group)

        assert reply.content.text == '🙅 Admin não pode ser bloqueado.'
        store.block_members.assert_not_called()

    @pytest.mark.anyio
    async def test_without_a_mention_asks_for_one(self, blocks, store, lid_group):
        reply = await blocks.apply(group_data(), 'bloquear', lid_group)

        assert reply.content.text == NO_TARGET
        lid_group.group_metadata.assert_not_called()
        store.block_members.assert_not_called()


class TestUnblock:
    @pytest.mark.anyio
    async def test_lifts_the_member_by_the_mentioned_form(self, blocks, store, lid_group):
        reply = await blocks.apply(group_data(LID), 'desbloquear', lid_group)

        store.unblock_members.assert_awaited_once_with(group_key(), [BlockedMember(key=LID)])
        assert reply.content.text == '✅ @123456789012345 liberado.'

    @pytest.mark.anyio
    async def test_without_a_mention_asks_for_one(self, blocks, store, lid_group):
        reply = await blocks.apply(group_data(), 'desbloquear', lid_group)

        assert reply.content.text == NO_TARGET
        store.unblock_members.assert_not_called()


class TestList:
    @pytest.mark.anyio
    async def test_mentions_each_blocked_member_once(self, blocks, store, lid_group):
        store.load.return_value = ChatConfig(blocked=(BlockedMember(key=PN, alt_key=LID),))

        reply = await blocks.apply(group_data(), 'bloqueados', lid_group)

        store.load.assert_awaited_once_with('whatsapp', GROUP)
        assert reply.content.text == 'Bloqueados neste grupo: @5527900000003'
        assert reply.content.mentions == [PN]

    @pytest.mark.anyio
    async def test_says_when_nobody_is_blocked(self, blocks, lid_group):
        reply = await blocks.apply(group_data(), 'bloqueados', lid_group)

        assert reply.content.text == 'Ninguém bloqueado neste grupo. ✅'


class TestUnsupported:
    @pytest.mark.anyio
    async def test_a_discord_chat(self, blocks, store, mock_whatsapp):
        data = GroupCommandDataFactory(platform='discord', mentioned_jids=[PN])

        reply = await blocks.apply(data, 'bloquear', mock_whatsapp)

        assert reply.content.text == UNSUPPORTED
        store.block_members.assert_not_called()

    @pytest.mark.anyio
    async def test_a_private_chat(self, blocks, mock_whatsapp):
        data = PrivateCommandDataFactory(platform='whatsapp')

        reply = await blocks.apply(data, 'bloqueados', mock_whatsapp)

        assert reply.content.text == UNSUPPORTED

    @pytest.mark.anyio
    async def test_no_whatsapp_port(self, blocks):
        reply = await blocks.apply(group_data(PN), 'bloquear', None)

        assert reply.content.text == UNSUPPORTED
