import httpx
import pytest

from bot.data.transfermarkt_urls import GLOBAL_URL, POSITION_FILTER_URL
from bot.domain.exceptions import TransfermarktBlockedError
from bot.domain.services.transfermarkt.client import TransfermarktClient

_WAF_CHALLENGE = httpx.Response(202, headers={'x-amzn-waf-action': 'challenge'})
_BLOCKED_RESPONSES = [
    pytest.param(_WAF_CHALLENGE, id='waf-challenge'),
    pytest.param(httpx.Response(202), id='accepted-empty'),
]


class TestBlocked:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    @pytest.mark.parametrize('response', _BLOCKED_RESPONSES)
    async def test_challenge_raises_blocked(self, respx_mock, response):
        respx_mock.get(url__startswith=GLOBAL_URL).mock(return_value=response)

        with pytest.raises(TransfermarktBlockedError):
            await TransfermarktClient.fetch_page(1)

    @pytest.mark.anyio
    async def test_blocked_position_pages_are_not_swallowed(self, respx_mock):
        respx_mock.get(url__startswith=POSITION_FILTER_URL).mock(return_value=_WAF_CHALLENGE)

        with pytest.raises(TransfermarktBlockedError):
            await TransfermarktClient.fetch_by_specific_position('GK', max_pages=1)

    @pytest.mark.anyio
    async def test_regular_page_is_parsed(self, respx_mock):
        respx_mock.get(url__startswith=GLOBAL_URL).mock(
            return_value=httpx.Response(200, text='<html></html>')
        )

        players = await TransfermarktClient.fetch_page(1)

        assert players == []
