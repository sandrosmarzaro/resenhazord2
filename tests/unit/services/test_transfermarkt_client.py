from pathlib import Path

import httpx
import pytest

from bot.data.football import LEAGUES
from bot.data.transfermarkt_urls import GLOBAL_URL, POSITION_FILTER_URL, SQUAD_VALUES_URL
from bot.domain.exceptions import TransfermarktBlockedError
from bot.domain.services.transfermarkt.client import TransfermarktClient

_FIXTURES = Path(__file__).parents[2] / 'fixtures' / 'html'
_CLUB_SQUAD_PREFIX = 'https://www.transfermarkt.com.br/club/kader/'
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
    async def test_blocked_club_squads_are_not_swallowed(self, respx_mock):
        league = LEAGUES['br']
        clubs_html = (_FIXTURES / 'league_clubs.html').read_text()
        squad_values_url = SQUAD_VALUES_URL.format(slug=league.tm_slug, tm_id=league.tm_id)
        respx_mock.get(squad_values_url).mock(return_value=httpx.Response(200, text=clubs_html))
        respx_mock.get(url__startswith=_CLUB_SQUAD_PREFIX).mock(return_value=_WAF_CHALLENGE)

        with pytest.raises(TransfermarktBlockedError):
            await TransfermarktClient.fetch_league_full_squad(league)

    @pytest.mark.anyio
    async def test_unblocked_position_pages_are_merged(self, respx_mock):
        respx_mock.get(url__startswith=POSITION_FILTER_URL).mock(
            return_value=httpx.Response(200, text='<html></html>')
        )

        players = await TransfermarktClient.fetch_by_specific_position('GK', max_pages=1)

        assert players == []

    @pytest.mark.anyio
    async def test_regular_page_is_parsed(self, respx_mock):
        respx_mock.get(url__startswith=GLOBAL_URL).mock(
            return_value=httpx.Response(200, text='<html></html>')
        )

        players = await TransfermarktClient.fetch_page(1)

        assert players == []
