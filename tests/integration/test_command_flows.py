import asyncio
import multiprocessing

import httpx
import pytest
import structlog
from redis.asyncio import Redis
from sqlalchemy import text
from testcontainers.rabbitmq import RabbitMqContainer

from bot.adapters.broker.command_consumer import CommandConsumer
from bot.application.command_handler import CommandHandler
from bot.application.command_registry import CommandRegistry
from bot.application.register_commands import register_all_commands
from bot.application.throttled_agent import ThrottledAgent
from bot.data.fifa_ratings import FIFA_RATINGS_URL
from bot.domain.commands.add import AddCommand
from bot.domain.commands.ban import BanCommand
from bot.domain.constants import COMMAND_OFF_IN_CHAT
from bot.domain.services.ytdlp import YtDlpService
from bot.infrastructure.broker import RabbitBroker
from bot.infrastructure.cached_config_store import CachedConfigStore
from bot.infrastructure.command_inbox import RedisCommandInbox
from bot.infrastructure.database import Database
from bot.infrastructure.models import Base
from bot.infrastructure.mongodb import MongoDBConnection
from bot.settings import Settings
from tests.integration.command_flow_harness import (
    ADMIN_JID,
    BOT_JID,
    GROUP_A,
    GROUP_B,
    MEMBER_JID,
    OTHER_JID,
    OWNER_JID,
    BotUnderTest,
    assert_local,
    ban_in_a_group_of_only_bot_and_owner,
    group_metadata,
    participant,
    texts,
)

FLOWS_DB = 'command_flows_test'
# The real ladder waits 30 s per hop. The retry queue gets its TTL at declare time, which
# is why this module runs its own broker.
RETRY_TTL_MS = 100
ADMIN_ONLY = 'Só admin pode usar esse comando. 🙅'
DEV_ONLY = 'Esse comando é apenas para desenvolvedores. 🛠️'
CREATED = 'Grupo *futebol* criado com sucesso! 🎉'
SKIPPED = frozenset({'command_redelivery_skipped', 'command_duplicate_skipped'})
HANG_SECONDS = 5


@pytest.fixture(scope='module')
def flows_rabbitmq_url():
    with RabbitMqContainer('rabbitmq:3.13') as container:
        params = container.get_connection_params()
        yield f'amqp://{container.username}:{container.password}@{params.host}:{params.port}/'


@pytest.fixture
def settings(monkeypatch, mongo_uri, postgres_url, redis_url, flows_rabbitmq_url) -> Settings:
    for url in (mongo_uri, postgres_url, redis_url, flows_rabbitmq_url):
        assert_local(url)
    monkeypatch.setenv('MONGODB_URI', mongo_uri)
    monkeypatch.setenv('MONGODB_DB_NAME', FLOWS_DB)
    monkeypatch.setenv('DATABASE_URL', postgres_url)
    monkeypatch.setenv('REDIS_URL', redis_url)
    monkeypatch.setenv('RABBITMQ_URL', flows_rabbitmq_url)
    monkeypatch.setenv('RESENHAZORD2_JID', BOT_JID)
    settings = Settings()
    # Environment variables must beat .env, whose URLs point at production.
    for url in (settings.mongodb_uri, settings.database_url, settings.redis_url):
        assert_local(url or '')
    assert settings.mongodb_db_name == FLOWS_DB
    return settings


@pytest.fixture
async def stores(settings, mongo_uri, postgres_url, redis_url):
    MongoDBConnection.reset()
    MongoDBConnection.configure(mongo_uri, db_name=FLOWS_DB)
    await MongoDBConnection.client().drop_database(FLOWS_DB)
    Database.reset()
    Database.configure(postgres_url)
    async with Database.engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        tables = ', '.join(Base.metadata.tables)
        await connection.execute(text(f'TRUNCATE {tables} RESTART IDENTITY CASCADE'))
    CachedConfigStore.reset()
    redis = Redis.from_url(redis_url)
    await redis.flushdb()
    await redis.aclose()

    yield

    await MongoDBConnection.close()
    await Database.close()


@pytest.fixture
def registry(settings, mock_whatsapp, mocker) -> CommandRegistry:
    # The agent graph is the LLM, an external service; nothing here routes to it.
    mocker.patch('bot.application.register_commands.build_agent_graph')
    register_all_commands(settings)
    registry = CommandRegistry.instance()
    registry.set_whatsapp(mock_whatsapp)
    return registry


@pytest.fixture
def handler(registry, mocker) -> CommandHandler:
    mocker.patch.object(CommandConsumer, 'RETRY_TTL_MS', RETRY_TTL_MS)
    agent = mocker.AsyncMock()
    agent.run.return_value = None
    return CommandHandler(registry, ThrottledAgent(agent, None))


@pytest.fixture
async def bot(stores, handler, flows_rabbitmq_url, redis_url, respx_mock):
    broker = RabbitBroker()
    await broker.connect(flows_rabbitmq_url)
    under_test = BotUnderTest(broker)
    previous = structlog.get_config()['processors']
    structlog.configure(processors=[under_test.logs])
    await under_test.start(CommandConsumer(broker, handler, RedisCommandInbox.from_url(redis_url)))

    yield under_test

    structlog.configure(processors=previous)
    await broker.close()


@pytest.fixture
def admins_group(mock_whatsapp):
    mock_whatsapp.group_metadata.return_value = group_metadata(
        participant(BOT_JID, admin='admin'),
        participant(OWNER_JID, admin='superadmin'),
        participant(ADMIN_JID, admin='admin'),
        participant(MEMBER_JID),
        participant(OTHER_JID),
    )
    return mock_whatsapp


async def make_dev(jid: str) -> None:
    await MongoDBConnection.collection('dev_list').insert_one({'_id': jid})


class TestCommandOverTheQueue:
    @pytest.mark.anyio
    async def test_a_matching_command_replies_under_the_same_id(self, bot):
        reply = await bot.send(',d20')

        assert texts(reply)[0].startswith('Aqui está sua rolada:')

    @pytest.mark.anyio
    async def test_no_matching_command_sends_nothing_but_closes_the_request(self, bot):
        reply = await bot.send('bom dia pessoal')

        assert reply['messages'] == []

    @pytest.mark.anyio
    async def test_a_business_error_replies_with_its_message(self, bot):
        word = 'a' * 250

        reply = await bot.send(f',áudio {word}')

        assert texts(reply) == [f'Word too long to split: {word[:200]}...']

    @pytest.mark.anyio
    async def test_a_failing_upstream_retries_then_dead_letters_with_an_error_reply(
        self, bot, respx_mock
    ):
        ratings = respx_mock.get(url__startswith=FIFA_RATINGS_URL).mock(
            return_value=httpx.Response(200, json={'items': []})
        )
        envelope = bot.envelope(',jogador fifa')

        await bot.publish(envelope)
        reply = await bot.reply_to(envelope)
        await bot.dead_letters.wait_for(lambda _: bool(bot.dead_letters.by_id(envelope['id'])))

        assert texts(reply) == ['Os ratings do EA FC não responderam agora. Tenta mais tarde! ⚽']
        assert ratings.call_count == CommandConsumer.MAX_ATTEMPTS

    @pytest.mark.anyio
    async def test_a_failed_download_dead_letters_without_the_retry_ladder(self, bot, mocker):
        download = mocker.patch.object(
            YtDlpService, 'download', side_effect=RuntimeError('ERROR: Unsupported URL')
        )
        envelope = bot.envelope(',dl https://example.com/video')

        await bot.publish(envelope)
        reply = await bot.reply_to(envelope)
        await bot.dead_letters.wait_for(lambda _: bool(bot.dead_letters.by_id(envelope['id'])))

        assert texts(reply) == ['Esse link não é suportado 🔗']
        assert download.await_count == 1


class TestRepeatedDelivery:
    @pytest.mark.anyio
    async def test_the_same_message_twice_in_a_row_replies_once(self, bot):
        envelope = bot.envelope(',d20')
        await bot.publish(envelope)
        await bot.reply_to(envelope)

        await bot.publish(envelope)
        await bot.logs.wait_for(lambda items: any(i['event'] in SKIPPED for i in items))

        assert len(bot.replies.by_id(envelope['id'])) == 1

    @pytest.mark.anyio
    async def test_the_same_message_twice_at_once_replies_once(self, bot):
        envelope = bot.envelope(',d20')

        await asyncio.gather(bot.publish(envelope), bot.publish(envelope))
        await bot.reply_to(envelope)
        await bot.logs.wait_for(lambda items: any(i['event'] in SKIPPED for i in items))

        assert len(bot.replies.by_id(envelope['id'])) == 1

    @pytest.mark.anyio
    async def test_the_same_message_id_in_another_chat_runs_both(self, bot):
        first = bot.envelope(',d20', jid=GROUP_A, message_id='SAME-ID')
        second = bot.envelope(',d20', jid=GROUP_B, message_id='SAME-ID')

        await asyncio.gather(bot.publish(first), bot.publish(second))

        assert texts(await bot.reply_to(first))
        assert texts(await bot.reply_to(second))

    @pytest.mark.anyio
    async def test_a_replayed_dead_letter_runs_again(self, bot):
        envelope = bot.envelope(',d20')
        await bot.publish(envelope)
        await bot.reply_to(envelope)

        await bot.publish({**envelope, 'replayed': True})
        await bot.replies.wait_for(lambda _: len(bot.replies.by_id(envelope['id'])) == 2)

        assert len(bot.replies.by_id(envelope['id'])) == 2


class TestDevScope:
    @pytest.mark.anyio
    async def test_a_non_dev_cannot_add_a_dev(self, bot):
        reply = await bot.send(',dev add', sender=MEMBER_JID, mentioned=[OTHER_JID])

        assert texts(reply) == [DEV_ONLY]
        assert await MongoDBConnection.collection('dev_list').count_documents({}) == 0

    @pytest.mark.anyio
    async def test_a_dev_adds_a_dev(self, bot):
        await make_dev(ADMIN_JID)

        await bot.send(',dev add', sender=ADMIN_JID, mentioned=[OTHER_JID])

        assert await MongoDBConnection.collection('dev_list').find_one({'_id': OTHER_JID})

    @pytest.mark.anyio
    @pytest.mark.parametrize(('suffix', 'runs'), [('3x', 3), ('9x', 5), ('0x', 1)])
    async def test_a_dev_batch_runs_up_to_the_cap(self, bot, suffix, runs):
        await make_dev(ADMIN_JID)

        reply = await bot.send(f',d20 {suffix}', sender=ADMIN_JID)

        assert len(reply['messages']) == runs

    @pytest.mark.anyio
    async def test_a_non_dev_batch_runs_once(self, bot):
        reply = await bot.send(',d20 3x', sender=MEMBER_JID)

        assert len(reply['messages']) == 1


class TestChatConfig:
    @pytest.mark.anyio
    async def test_a_member_cannot_turn_a_command_off(self, bot, admins_group):
        refused = await bot.send(',config off d20', sender=MEMBER_JID)

        rolled = await bot.send(',d20', sender=MEMBER_JID)

        assert texts(refused) == ['Só admin configura os comandos do chat. 🙅']
        assert texts(rolled)[0].startswith('Aqui está sua rolada:')

    @pytest.mark.anyio
    async def test_an_admin_turns_a_command_off_in_the_chat(self, bot, admins_group):
        await bot.send(',config off d20', sender=ADMIN_JID)

        reply = await bot.send(',d20', sender=MEMBER_JID)

        assert texts(reply) == [COMMAND_OFF_IN_CHAT]

    @pytest.mark.anyio
    async def test_turning_a_command_off_leaves_other_chats_alone(self, bot, admins_group):
        await bot.send(',config off d20', sender=ADMIN_JID, jid=GROUP_A)

        reply = await bot.send(',d20', sender=MEMBER_JID, jid=GROUP_B)

        assert texts(reply)[0].startswith('Aqui está sua rolada:')

    @pytest.mark.anyio
    async def test_the_same_change_twice_at_once_stores_one_override(self, bot, admins_group):
        first = bot.envelope(',config off d20', sender=ADMIN_JID)
        second = bot.envelope(',config off d20', sender=ADMIN_JID)

        await asyncio.gather(bot.publish(first), bot.publish(second))
        await bot.reply_to(first)
        await bot.reply_to(second)

        async with Database.engine().connect() as connection:
            count = await connection.scalar(text('SELECT count(*) FROM command_override'))
        assert count == 1

    @pytest.mark.anyio
    async def test_nsfw_stays_blocked_until_an_admin_allows_it(self, bot, admins_group):
        reply = await bot.send(',hentai', sender=MEMBER_JID)

        assert texts(reply) == [COMMAND_OFF_IN_CHAT]


class TestBan:
    @pytest.mark.anyio
    async def test_refuses_when_the_bot_is_not_admin(self, bot, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = group_metadata(
            participant(BOT_JID), participant(ADMIN_JID, admin='admin'), participant(MEMBER_JID)
        )

        reply = await bot.send(',ban', sender=ADMIN_JID, mentioned=[MEMBER_JID])

        assert texts(reply) == [BanCommand.BOT_NOT_ADMIN_MSG]
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_a_member_cannot_ban(self, bot, admins_group):
        reply = await bot.send(',ban', sender=MEMBER_JID, mentioned=[OTHER_JID])

        assert texts(reply) == [ADMIN_ONLY]
        admins_group.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_an_admin_bans_the_mentioned_member(self, bot, admins_group):
        await bot.send(',ban', sender=ADMIN_JID, mentioned=[MEMBER_JID])

        admins_group.group_participants_update.assert_awaited_once_with(
            GROUP_A, [MEMBER_JID], 'remove'
        )

    @pytest.mark.anyio
    async def test_never_bans_the_bot_or_an_admin_owner(self, bot, admins_group):
        await bot.send(',ban', sender=ADMIN_JID, mentioned=[BOT_JID, OWNER_JID])

        admins_group.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_a_random_ban_spares_the_bot_and_the_owner(self, bot, admins_group):
        await bot.send(',ban', sender=ADMIN_JID)

        removed = admins_group.group_participants_update.await_args.args[1]
        assert removed[0] not in {BOT_JID, OWNER_JID}

    # A busy loop never yields to the event loop, so no asyncio timeout can stop it. A
    # child process can be stopped from outside.
    def test_a_random_ban_with_only_the_bot_and_the_owner_left_returns(self):
        process = multiprocessing.get_context('spawn').Process(
            target=ban_in_a_group_of_only_bot_and_owner, daemon=True
        )

        process.start()
        process.join(HANG_SECONDS)
        hung = process.is_alive()
        process.terminate()

        assert not hung


class TestAdd:
    @pytest.mark.anyio
    async def test_refuses_when_the_bot_is_not_admin(self, bot, mock_whatsapp):
        mock_whatsapp.group_metadata.return_value = group_metadata(
            participant(BOT_JID), participant(ADMIN_JID, admin='admin')
        )

        reply = await bot.send(',add 27999990000', sender=ADMIN_JID)

        assert texts(reply) == [AddCommand.BOT_NOT_ADMIN_MSG]
        mock_whatsapp.group_participants_update.assert_not_called()

    @pytest.mark.anyio
    async def test_a_member_cannot_add(self, bot, admins_group):
        reply = await bot.send(',add 27999990000', sender=MEMBER_JID)

        assert texts(reply) == [ADMIN_ONLY]
        admins_group.on_whatsapp.assert_not_called()

    @pytest.mark.anyio
    async def test_an_invalid_area_code_is_refused_before_whatsapp(self, bot, admins_group):
        reply = await bot.send(',add 00999990000', sender=ADMIN_JID)

        assert texts(reply) == [AddCommand.INVALID_DDD_MSG]
        admins_group.on_whatsapp.assert_not_called()

    @pytest.mark.anyio
    async def test_an_admin_adds_a_number(self, bot, admins_group):
        added = '5527999990000@s.whatsapp.net'
        admins_group.on_whatsapp.return_value = [{'exists': True, 'jid': added}]

        await bot.send(',add 27999990000', sender=ADMIN_JID)

        admins_group.group_participants_update.assert_awaited_once_with(GROUP_A, [added], 'add')


class TestMentionLists:
    @pytest.mark.anyio
    async def test_a_created_list_mentions_its_creator_and_members(self, bot):
        await bot.send(',grupo create futebol', sender=MEMBER_JID, mentioned=[OTHER_JID])

        reply = await bot.send(',grupo futebol')

        assert texts(reply) == ['@5527900000003 @5527900000004']

    @pytest.mark.anyio
    async def test_leaving_drops_only_the_sender(self, bot):
        await bot.send(',grupo create futebol', sender=MEMBER_JID, mentioned=[OTHER_JID])
        await bot.send(',grupo exit futebol', sender=MEMBER_JID)

        reply = await bot.send(',grupo futebol')

        assert texts(reply) == ['@5527900000004']

    @pytest.mark.anyio
    async def test_any_member_can_remove_someone_else(self, bot):
        await bot.send(',grupo create futebol', sender=MEMBER_JID, mentioned=[OTHER_JID])
        await bot.send(',grupo exit futebol', sender=ADMIN_JID, mentioned=[OTHER_JID])

        reply = await bot.send(',grupo futebol')

        assert texts(reply) == ['@5527900000003']

    @pytest.mark.anyio
    async def test_any_member_can_rename_and_delete_a_list_created_by_another(self, bot):
        await bot.send(',grupo create futebol', sender=MEMBER_JID)

        renamed = await bot.send(',grupo rename futebol bola', sender=OTHER_JID)
        deleted = await bot.send(',grupo delete bola', sender=OTHER_JID)

        assert texts(renamed) == ['Grupo *futebol* renomeado para *bola* com sucesso! 🎉']
        assert texts(deleted) == ['Grupo *bola* deletado com sucesso! 🎉']

    @pytest.mark.anyio
    async def test_a_list_stays_in_its_own_chat(self, bot):
        await bot.send(',grupo create futebol', sender=MEMBER_JID, jid=GROUP_A)
        await bot.send(',grupo delete futebol', sender=MEMBER_JID, jid=GROUP_B)

        reply = await bot.send(',grupo futebol', jid=GROUP_A)

        assert texts(reply) == ['@5527900000003']

    @pytest.mark.anyio
    async def test_the_same_creation_twice_at_once_creates_one_list(self, bot):
        first = bot.envelope(',grupo create futebol', sender=MEMBER_JID)
        second = bot.envelope(',grupo create futebol', sender=OTHER_JID)

        await asyncio.gather(bot.publish(first), bot.publish(second))
        replies = [texts(await bot.reply_to(first)), texts(await bot.reply_to(second))]

        created = [reply for reply in replies if reply == [CREATED]]
        assert len(created) == 1


class TestBirthdays:
    @pytest.mark.anyio
    async def test_a_member_registers_lists_and_removes_their_birthday(self, bot):
        await bot.send(',niver 21/02', sender=MEMBER_JID)
        listed = await bot.send(',niver')
        await bot.send(',niver remove', sender=MEMBER_JID)

        emptied = await bot.send(',niver')

        assert texts(listed) == ['🎂 *ANIVERSÁRIOS* 🎂\n\n- 21/02 @5527900000003']
        assert texts(emptied) == ['Ninguém cadastrou aniversário ainda 🎈']

    @pytest.mark.anyio
    @pytest.mark.parametrize('impossible', ['31/02', '00/13'])
    async def test_an_impossible_date_stores_nothing(self, bot, impossible):
        await bot.send(f',niver {impossible}', sender=MEMBER_JID)

        reply = await bot.send(',niver')

        assert texts(reply) == ['Ninguém cadastrou aniversário ainda 🎈']

    @pytest.mark.anyio
    async def test_february_29_is_accepted(self, bot):
        reply = await bot.send(',niver 29/02', sender=MEMBER_JID)

        assert texts(reply) == ['🎂 Anotado!\n\n- @5527900000003 29/02']

    @pytest.mark.anyio
    async def test_registering_again_replaces_the_date(self, bot):
        await bot.send(',niver 21/02', sender=MEMBER_JID)
        await bot.send(',niver 22/02', sender=MEMBER_JID)

        reply = await bot.send(',niver')

        assert texts(reply) == ['🎂 *ANIVERSÁRIOS* 🎂\n\n- 22/02 @5527900000003']

    @pytest.mark.anyio
    async def test_a_birthday_stays_in_its_own_chat(self, bot):
        await bot.send(',niver 21/02', sender=MEMBER_JID, jid=GROUP_A)

        reply = await bot.send(',niver', jid=GROUP_B)

        assert texts(reply) == ['Ninguém cadastrou aniversário ainda 🎈']

    @pytest.mark.anyio
    async def test_any_member_can_register_and_remove_someone_else(self, bot):
        await bot.send(',niver @5527900000004 01/12', sender=MEMBER_JID, mentioned=[OTHER_JID])
        listed = await bot.send(',niver')
        await bot.send(',niver remove', sender=MEMBER_JID, mentioned=[OTHER_JID])

        emptied = await bot.send(',niver')

        assert texts(listed) == ['🎂 *ANIVERSÁRIOS* 🎂\n\n- 01/12 @5527900000004']
        assert texts(emptied) == ['Ninguém cadastrou aniversário ainda 🎈']


class TestCounter:
    @pytest.mark.anyio
    async def test_the_same_message_twice_counts_once(self, bot):
        envelope = bot.envelope(',borges')
        await bot.publish(envelope)
        await bot.reply_to(envelope)
        await bot.publish(envelope)
        await bot.logs.wait_for(lambda items: any(i['event'] in SKIPPED for i in items))

        reply = await bot.send(',borges')

        assert texts(reply) == ['Borges já fumou 2 nargas 🚬']

    @pytest.mark.anyio
    async def test_two_messages_at_once_count_twice(self, bot):
        first = bot.envelope(',borges')
        second = bot.envelope(',borges')
        await asyncio.gather(bot.publish(first), bot.publish(second))
        await bot.reply_to(first)
        await bot.reply_to(second)

        reply = await bot.send(',borges')

        assert texts(reply) == ['Borges já fumou 3 nargas 🚬']
