import pytest
from fakeredis.aioredis import FakeRedis

from bot.infrastructure.issue_filings import IssueFilings

KEY = 'whatsapp:g@g.us:MSG-1'
URL = 'https://github.com/owner/repo/issues/432'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def filings():
    return IssueFilings(FakeRedis())


class TestClaim:
    @pytest.mark.anyio
    async def test_the_first_claim_wins(self, filings):
        assert await filings.claim(KEY) is None

    @pytest.mark.anyio
    async def test_a_second_claim_sees_the_filing_in_progress(self, filings):
        await filings.claim(KEY)

        assert await filings.claim(KEY) == IssueFilings.IN_PROGRESS

    @pytest.mark.anyio
    async def test_a_settled_filing_hands_back_its_issue(self, filings):
        await filings.claim(KEY)
        await filings.settle(KEY, URL)

        assert await filings.claim(KEY) == URL

    @pytest.mark.anyio
    async def test_a_released_claim_can_be_taken_again(self, filings):
        await filings.claim(KEY)
        await filings.release(KEY)

        assert await filings.claim(KEY) is None

    @pytest.mark.anyio
    async def test_a_claim_expires(self):
        redis = FakeRedis()
        await IssueFilings(redis).claim(KEY)

        assert await redis.ttl(f'bug_issue:{KEY}') == IssueFilings.RETENTION_SECONDS
