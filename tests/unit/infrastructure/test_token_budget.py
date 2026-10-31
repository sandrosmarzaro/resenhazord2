from datetime import datetime

import pytest
from fakeredis.aioredis import FakeRedis
from structlog.testing import capture_logs

from bot.domain.models.command_data import CommandData
from bot.infrastructure.token_budget import TokenBudget, TokenBudgetPolicy
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

_MODULE = 'bot.infrastructure.token_budget'
_NOW = 1_800_000_000.0
_USER_PER_DAY = 86_400
_GROUP_PER_DAY = 3 * _USER_PER_DAY
_OWNER = '5511999990000@s.whatsapp.net'
_GROUP = '120363000000000001@g.us'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def clock(mocker):
    return mocker.patch(f'{_MODULE}.time.time', return_value=_NOW)


def _policy(*, enforce: bool = True) -> TokenBudgetPolicy:
    return TokenBudgetPolicy(
        _USER_PER_DAY, _GROUP_PER_DAY, enforce=enforce, owners=frozenset({_OWNER})
    )


def _budget(*, enforce: bool = True) -> TokenBudget:
    return TokenBudget(FakeRedis(), _policy(enforce=enforce))


def _member(sender: str) -> CommandData:
    return GroupCommandDataFactory.build(jid=_GROUP, sender_jid=sender)


class TestRefillAt:
    @pytest.mark.anyio
    async def test_a_fresh_sender_is_allowed(self, clock):
        assert await _budget().refill_at(PrivateCommandDataFactory.build()) is None

    @pytest.mark.anyio
    async def test_an_overspent_sender_waits_for_the_refill(self, clock):
        budget = _budget()
        data = PrivateCommandDataFactory.build()
        # One token per second refills a 60-token overdraft in a minute, plus the token
        # that makes the balance positive.
        await budget.spend(data, _USER_PER_DAY + 60)

        refill = await budget.refill_at(data)

        assert refill == datetime.fromtimestamp(_NOW + 61, TokenBudget.TIMEZONE)

    @pytest.mark.anyio
    async def test_the_bucket_refills_over_time(self, clock):
        budget = _budget()
        data = PrivateCommandDataFactory.build()
        await budget.spend(data, _USER_PER_DAY + 60)
        clock.return_value = _NOW + 61

        assert await budget.refill_at(data) is None

    @pytest.mark.anyio
    async def test_an_overspent_group_blocks_its_other_members(self, clock):
        budget = _budget()
        for sender in ('a', 'b', 'c'):
            await budget.spend(_member(sender), _USER_PER_DAY)

        assert await budget.refill_at(_member('d')) is not None

    @pytest.mark.anyio
    async def test_the_owner_is_exempt(self, clock):
        budget = _budget()
        owner = _member(_OWNER)
        await budget.spend(owner, 10 * _GROUP_PER_DAY)

        assert await budget.refill_at(owner) is None

    @pytest.mark.anyio
    async def test_a_dry_run_only_records_the_rejection(self, clock, mocker):
        record = mocker.patch(f'{_MODULE}.record_agent_budget_rejection')
        budget = _budget(enforce=False)
        data = PrivateCommandDataFactory.build()
        await budget.spend(data, _USER_PER_DAY + 60)

        refill = await budget.refill_at(data)

        assert refill is None
        record.assert_called_once_with('user', enforced=False)

    @pytest.mark.anyio
    async def test_fails_open_without_redis(self):
        budget = TokenBudget.from_url('redis://127.0.0.1:1', _policy())

        assert await budget.refill_at(PrivateCommandDataFactory.build()) is None


class TestSpend:
    @pytest.mark.anyio
    async def test_records_the_tokens_spent(self, clock, mocker):
        record = mocker.patch(f'{_MODULE}.record_agent_tokens')

        await _budget().spend(PrivateCommandDataFactory.build(), 7460)

        record.assert_called_once_with(7460)

    @pytest.mark.anyio
    async def test_a_full_bucket_expires(self, clock):
        redis = FakeRedis()
        await TokenBudget(redis, _policy()).spend(PrivateCommandDataFactory.build(), 60)

        [key] = await redis.keys()
        assert await redis.ttl(key) == 60

    @pytest.mark.anyio
    async def test_survives_redis_errors(self):
        budget = TokenBudget.from_url('redis://127.0.0.1:1', _policy())

        with capture_logs() as logs:
            await budget.spend(PrivateCommandDataFactory.build(), 7460)

        assert [log['event'] for log in logs] == ['agent_budget_unavailable']
