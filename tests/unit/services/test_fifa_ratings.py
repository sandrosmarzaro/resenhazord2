from datetime import timedelta

import httpx
import pytest

from bot.data.fifa_ratings import FIFA_RATINGS_URL
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.football import FifaPlayer
from bot.domain.services.fifa_ratings import FifaRatings

_CARD = 'https://ratings-images-prod.pulse.ea.com/FC25/full/player-shields/en/209331.png'


def _item(first: str, last: str, overall: int, **overrides) -> dict:
    return {
        'firstName': first,
        'lastName': last,
        'commonName': None,
        'overallRating': overall,
        'shieldUrl': _CARD,
        **overrides,
    }


def _page(*items: dict) -> httpx.Response:
    return httpx.Response(200, json={'items': list(items), 'totalItems': len(items)})


@pytest.fixture(autouse=True)
def empty_cache(mocker):
    mocker.patch.object(FifaRatings, '_cache', {})


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def strikers(respx_mock):
    return respx_mock.get(FIFA_RATINGS_URL, params={'position': '25'}).mock(
        return_value=_page(_item('Mohamed', 'Salah', 91), _item('Kylian', 'Mbappé', 90))
    )


class TestRolePools:
    @pytest.mark.anyio
    async def test_maps_the_best_men_of_each_position(self, strikers):
        pools = await FifaRatings.role_pools({'ST'})

        assert pools['ST'][0] == FifaPlayer(name='Mohamed Salah', overall=91, card_url=_CARD)
        params = strikers.calls.last.request.url.params
        assert (params['gender'], params['limit']) == ('0', '100')

    @pytest.mark.anyio
    async def test_prefers_the_common_name(self, respx_mock):
        respx_mock.get(FIFA_RATINGS_URL, params={'position': '0'}).mock(
            return_value=_page(_item('Alisson', 'Ramses Becker', 89, commonName='Alisson'))
        )

        pools = await FifaRatings.role_pools({'GK'})

        assert pools['GK'][0].name == 'Alisson'

    @pytest.mark.anyio
    async def test_drops_cards_outside_ea_hosts(self, respx_mock):
        tampered = _item('Tampered', 'Player', 80, shieldUrl='http://169.254.169.254/latest')
        respx_mock.get(FIFA_RATINGS_URL, params={'position': '25'}).mock(
            return_value=_page(tampered)
        )

        pools = await FifaRatings.role_pools({'ST'})

        assert pools['ST'][0].card_url == ''

    @pytest.mark.anyio
    async def test_empty_position_is_an_upstream_failure(self, respx_mock):
        respx_mock.get(FIFA_RATINGS_URL, params={'position': '25'}).mock(return_value=_page())

        with pytest.raises(ExternalServiceError):
            await FifaRatings.role_pools({'ST'})


class TestTop:
    @pytest.mark.anyio
    async def test_ranks_every_position_together(self, respx_mock):
        route = respx_mock.get(FIFA_RATINGS_URL).mock(
            return_value=_page(_item('Mohamed', 'Salah', 91))
        )

        players = await FifaRatings.top()

        assert players[0].name == 'Mohamed Salah'
        assert 'position' not in route.calls.last.request.url.params


class TestCache:
    @pytest.mark.anyio
    async def test_reuses_a_position_within_ttl(self, strikers):
        await FifaRatings.role_pools({'ST'})
        await FifaRatings.role_pools({'ST'})

        assert strikers.call_count == 1

    @pytest.mark.anyio
    async def test_refetches_after_ttl(self, strikers, mocker):
        mocker.patch.object(FifaRatings, '_TTL', timedelta(0))

        await FifaRatings.role_pools({'ST'})
        await FifaRatings.role_pools({'ST'})

        assert strikers.call_count == 2
