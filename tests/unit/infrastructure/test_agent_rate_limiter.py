import pytest
from fakeredis.aioredis import FakeRedis

from bot.infrastructure.agent_rate_limiter import AgentRateLimiter


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def redis():
    return FakeRedis()


@pytest.fixture
def limiter(redis):
    return AgentRateLimiter(redis)


async def _exhaust(limiter: AgentRateLimiter, conversation: str) -> None:
    for _ in range(AgentRateLimiter.MAX_TURNS):
        await limiter.allow(conversation)


class TestAllow:
    @pytest.mark.anyio
    async def test_allows_turns_up_to_the_limit(self, limiter):
        results = [await limiter.allow('dm:vivo') for _ in range(AgentRateLimiter.MAX_TURNS)]

        assert all(results)

    @pytest.mark.anyio
    async def test_denies_the_turn_past_the_limit(self, limiter):
        await _exhaust(limiter, 'dm:vivo')

        assert await limiter.allow('dm:vivo') is False

    @pytest.mark.anyio
    async def test_counts_each_conversation_separately(self, limiter):
        await _exhaust(limiter, 'dm:vivo')

        assert await limiter.allow('dm:friend') is True

    @pytest.mark.anyio
    async def test_window_expires(self, limiter, redis):
        await limiter.allow('dm:vivo')

        [key] = await redis.keys()
        assert 0 < await redis.ttl(key) <= AgentRateLimiter.WINDOW_SECONDS


class TestLoopAlert:
    @pytest.mark.anyio
    async def test_reports_a_tripped_window_once(self, limiter, mocker):
        capture = mocker.patch('bot.infrastructure.agent_rate_limiter.sentry_sdk.capture_message')
        await _exhaust(limiter, 'dm:vivo')

        await limiter.allow('dm:vivo')
        await limiter.allow('dm:vivo')

        capture.assert_called_once_with('agent_rate_limited', level='warning')


class TestRedisUnavailable:
    @pytest.mark.anyio
    async def test_fails_open(self):
        limiter = AgentRateLimiter.from_url('redis://127.0.0.1:1')

        assert await limiter.allow('dm:vivo') is True
