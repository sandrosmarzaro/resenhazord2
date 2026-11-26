import pytest
import sentry_sdk
from fakeredis.aioredis import FakeRedis

from bot.domain.commands.base import Platform
from bot.infrastructure.command_trail import CommandTrail
from bot.infrastructure.execution_store import ExecutionStore
from bot.infrastructure.telemetry_buffer import TelemetryBuffer
from bot.infrastructure.telemetry_redactor import TelemetryRedactor
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def store():
    store = ExecutionStore(FakeRedis())
    ExecutionStore.reset(store)
    return store


@pytest.fixture
def data():
    return GroupCommandDataFactory(text=',moeda iene', platform=Platform.WHATSAPP)


async def _record(store, data, message_id='3EB0A'):
    return await store.find(Platform.WHATSAPP, data.jid, message_id)


class TestCurrent:
    def test_no_trail_is_open_outside_a_command(self):
        assert CommandTrail.current() is None

    @pytest.mark.anyio
    async def test_the_open_trail_is_current(self, store, data):
        async with CommandTrail.open(data) as trail:
            assert CommandTrail.current() is trail

    @pytest.mark.anyio
    async def test_closing_clears_the_current_trail(self, store, data):
        async with CommandTrail.open(data):
            pass

        assert CommandTrail.current() is None


class TestRecord:
    @pytest.mark.anyio
    async def test_is_stored_under_each_reply(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember('3EB0A', 'primeira')
            trail.remember('3EB0B', 'segunda')

        assert await _record(store, data, '3EB0B') == await _record(store, data, '3EB0A')

    @pytest.mark.anyio
    async def test_keeps_what_each_reply_said(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember('3EB0A', '¥1 = R$0,03')

        assert (await _record(store, data))['replies'] == {'3EB0A': '¥1 = R$0,03'}

    @pytest.mark.anyio
    async def test_a_reply_without_an_id_is_not_kept(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember(None, 'status')

        assert await store.find(Platform.WHATSAPP, data.jid, 'None') is None

    @pytest.mark.anyio
    async def test_carries_where_the_command_came_from(self, store, data):
        async with CommandTrail.open(data, correlation_id='corr-1', attempt=2) as trail:
            trail.remember('3EB0A', 'ok')

        record = await _record(store, data)
        assert {key: record[key] for key in ('platform', 'chat_type', 'correlation_id')} == {
            'platform': 'whatsapp',
            'chat_type': 'group',
            'correlation_id': 'corr-1',
        }

    @pytest.mark.anyio
    async def test_hashes_the_chat_and_the_sender(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember('3EB0A', 'ok')

        record = await _record(store, data)
        assert (record['chat'], record['sender']) == (
            TelemetryRedactor.identity(data.jid),
            TelemetryRedactor.identity(data.sender_jid),
        )

    @pytest.mark.anyio
    async def test_counts_the_attempt(self, store, data):
        async with CommandTrail.open(data, attempt=3) as trail:
            trail.remember('3EB0A', 'ok')

        assert (await _record(store, data))['attempt'] == 3

    @pytest.mark.anyio
    async def test_a_command_without_a_correlation_id_gets_one(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember('3EB0A', 'ok')

        assert (await _record(store, data))['correlation_id']

    @pytest.mark.anyio
    async def test_keeps_the_execution(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.execution = {'command': 'moeda'}
            trail.remember('3EB0A', 'ok')

        assert (await _record(store, data))['execution'] == {'command': 'moeda'}

    @pytest.mark.anyio
    async def test_keeps_the_captured_spans_and_logs(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.spans.append({'name': 'command.run'})
            trail.logs.append({'event': 'command_completed'})
            trail.remember('3EB0A', 'ok')

        record = await _record(store, data)
        assert (record['spans'], record['logs']) == (
            [{'name': 'command.run'}],
            [{'event': 'command_completed'}],
        )

    @pytest.mark.anyio
    async def test_takes_a_host_snapshot(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.remember('3EB0A', 'ok')

        assert (await _record(store, data))['host']['rss_bytes'] > 0


class TestRelease:
    @pytest.mark.anyio
    async def test_closing_releases_the_buffers(self, store, data):
        async with CommandTrail.open(data) as trail:
            trail.spans.append({'name': 'command.run'})

        assert TelemetryBuffer.held() == 0

    @pytest.mark.anyio
    async def test_a_failing_command_still_releases_them(self, store, data):
        async def fail():
            async with CommandTrail.open(data) as trail:
                trail.logs.append({'event': 'boom'})
                raise RuntimeError

        with pytest.raises(RuntimeError):
            await fail()

        assert TelemetryBuffer.held() == 0


class TestSentry:
    @pytest.mark.anyio
    async def test_tags_sentry_events_with_the_correlation_id(self, store, data):
        async with CommandTrail.open(data, correlation_id='corr-1'):
            tags = sentry_sdk.get_isolation_scope()._tags

        assert tags['correlation_id'] == 'corr-1'

    @pytest.mark.anyio
    async def test_the_tag_does_not_outlive_the_command(self, store, data):
        async with CommandTrail.open(data, correlation_id='corr-1'):
            pass

        assert 'correlation_id' not in sentry_sdk.get_isolation_scope()._tags
