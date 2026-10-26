import csv
import gzip
import io
from datetime import datetime, timedelta

import httpx
import pytest

from bot.data.football import BR_TIMEZONE
from bot.data.market_dataset import MARKET_DATASET_URL
from bot.domain.models.football import PlayerProfile, TmPlayer, TmSquadStats
from bot.domain.services.market_dataset import MarketDataset

_PLAYERS_URL = MARKET_DATASET_URL.format(table='players')
_CLUBS_URL = MARKET_DATASET_URL.format(table='clubs')
_FRESH = 'Sat, 05 Sep 2099 09:12:22 GMT'
_STALE = 'Sat, 05 Sep 2020 09:12:22 GMT'


def _player(name: str, value: str, **overrides: str) -> dict[str, str]:
    return {
        'name': name,
        'last_season': '2025',
        'sub_position': 'Centre-Forward',
        'date_of_birth': '2000-01-01 00:00:00',
        'country_of_citizenship': 'Norway',
        'current_club_id': '281',
        'current_club_name': 'Manchester City',
        'current_club_domestic_competition_id': 'GB1',
        'market_value_in_eur': value,
        'image_url': f'https://img.a.transfermarkt.technology/portrait/header/{name}.jpg',
        'city_of_birth': 'Leeds\xa0\xa0',
        'country_of_birth': 'England',
        'height_in_cm': '195',
        'foot': 'left',
        **overrides,
    }


def _club(club_id: str, name: str, league_id: str, last_season: str = '2025') -> dict[str, str]:
    return {
        'club_id': club_id,
        'name': name,
        'domestic_competition_id': league_id,
        'last_season': last_season,
        'squad_size': '25',
        'average_age': '26.3',
        'foreigners_number': '15',
        'foreigners_percentage': '60.0',
    }


_PLAYERS = [
    _player('Foden', '120000000'),
    _player('Haaland', '200000000'),
    _player('Kid', '500000', date_of_birth=''),
    _player('Unpriced', ''),
    _player('Retired', '1000000', last_season='2023'),
    _player(
        'Vitor Roque',
        '30000000',
        current_club_id='1023',
        current_club_name='Palmeiras',
        current_club_domestic_competition_id='BRA1',
        country_of_citizenship='Brazil',
    ),
]
_CLUBS = [
    _club('281', 'Manchester City', 'GB1'),
    _club('1023', 'Palmeiras', 'BRA1'),
    _club('985', 'Old Club', 'GB1', last_season='2023'),
    _club('77', 'Sem Valor Futebol Clube', 'BRA1'),
]


def _gzip_csv(rows: list[dict[str, str]]) -> bytes:
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return gzip.compress(text.getvalue().encode())


@pytest.fixture(autouse=True)
def empty_cache(mocker):
    mocker.patch.object(MarketDataset, '_snapshot', None)


@pytest.fixture
def dataset_routes(respx_mock):
    def mount(last_modified: str = _FRESH):
        players = respx_mock.get(_PLAYERS_URL).mock(
            return_value=httpx.Response(
                200, content=_gzip_csv(_PLAYERS), headers={'last-modified': last_modified}
            )
        )
        clubs = respx_mock.get(_CLUBS_URL).mock(
            return_value=httpx.Response(200, content=_gzip_csv(_CLUBS))
        )
        return players, clubs

    return mount


class TestPlayers:
    @pytest.mark.anyio
    async def test_maps_current_priced_players_by_value(self, dataset_routes):
        dataset_routes()

        players = await MarketDataset.players()

        assert players[0] == TmPlayer(
            name='Haaland',
            position='Centre-Forward',
            age=datetime.now(BR_TIMEZONE).year - 2000,
            nationality='Norway',
            club='Manchester City',
            club_id='281',
            market_value=200_000_000,
            photo_url='https://img.a.transfermarkt.technology/portrait/header/Haaland.jpg',
            badge_url='https://tmssl.akamaized.net/images/wappen/head/281.png',
            nationality_flag_emoji='🇳🇴',
            profile=PlayerProfile(
                birth_city='Leeds', birth_country='England', height_cm='195', foot='left'
            ),
        )
        assert [player.name for player in players] == ['Haaland', 'Foden', 'Vitor Roque', 'Kid']

    @pytest.mark.anyio
    async def test_formats_values_under_a_million_in_thousands(self, dataset_routes):
        dataset_routes()

        players = await MarketDataset.players()

        assert MarketDataset.format_euros(players[-1].market_value) == '€ 500 mil.'

    @pytest.mark.anyio
    async def test_filters_by_league(self, dataset_routes):
        dataset_routes()

        players = await MarketDataset.players('BRA1')

        assert [player.name for player in players] == ['Vitor Roque']

    @pytest.mark.anyio
    async def test_unknown_birth_date_has_no_age(self, dataset_routes):
        dataset_routes()

        players = await MarketDataset.players()

        assert players[-1].age == 0

    @pytest.mark.anyio
    async def test_drops_assets_outside_transfermarkt_cdn(self, respx_mock):
        tampered = _player(
            'Tampered',
            '1000000',
            image_url='http://169.254.169.254/latest/meta-data',
            current_club_id='../admin',
        )
        respx_mock.get(_PLAYERS_URL).mock(
            return_value=httpx.Response(200, content=_gzip_csv([tampered]))
        )
        respx_mock.get(_CLUBS_URL).mock(return_value=httpx.Response(200, content=_gzip_csv(_CLUBS)))

        players = await MarketDataset.players()

        assert (players[0].photo_url, players[0].badge_url) == ('', '')


class TestClubs:
    @pytest.mark.anyio
    async def test_sums_squad_value_and_keeps_current_clubs(self, dataset_routes):
        dataset_routes()

        clubs = await MarketDataset.clubs()

        assert clubs == [
            TmSquadStats(
                market_value='€ 320,50 mi.',
                squad_size='25',
                avg_age='26,3',
                foreigners_count='15',
                foreigners_pct='60,0',
                club_id='281',
                name='Manchester City',
                badge_url='https://tmssl.akamaized.net/images/wappen/head/281.png',
                league_id='GB1',
            ),
            TmSquadStats(
                market_value='€ 30,00 mi.',
                squad_size='25',
                avg_age='26,3',
                foreigners_count='15',
                foreigners_pct='60,0',
                club_id='1023',
                name='Palmeiras',
                badge_url='https://tmssl.akamaized.net/images/wappen/head/1023.png',
                league_id='BRA1',
            ),
            TmSquadStats(
                market_value='€ 0 mil.',
                squad_size='25',
                avg_age='26,3',
                foreigners_count='15',
                foreigners_pct='60,0',
                club_id='77',
                name='Sem Valor Futebol Clube',
                badge_url='https://tmssl.akamaized.net/images/wappen/head/77.png',
                league_id='BRA1',
            ),
        ]

    @pytest.mark.anyio
    async def test_filters_by_league(self, dataset_routes):
        dataset_routes()

        clubs = await MarketDataset.clubs('BRA1')

        assert [club.name for club in clubs] == ['Palmeiras', 'Sem Valor Futebol Clube']


class TestCache:
    @pytest.mark.anyio
    async def test_reuses_snapshot_within_ttl(self, dataset_routes):
        players_route, _ = dataset_routes()

        await MarketDataset.players()
        await MarketDataset.clubs()

        assert players_route.call_count == 1

    @pytest.mark.anyio
    async def test_reloads_after_ttl(self, dataset_routes, mocker):
        players_route, _ = dataset_routes()
        mocker.patch.object(MarketDataset, '_TTL', timedelta(0))

        await MarketDataset.players()
        await MarketDataset.players()

        assert players_route.call_count == 2

    @pytest.mark.anyio
    async def test_warns_when_upstream_stopped_publishing(self, dataset_routes, mocker):
        dataset_routes(last_modified=_STALE)
        logger = mocker.patch('bot.domain.services.market_dataset.logger')

        await MarketDataset.players()

        logger.warning.assert_called_once_with('market_dataset_stale', last_modified=_STALE)


class TestFormatEuros:
    @pytest.mark.parametrize(
        ('euros', 'label'),
        [
            (500_000, '€ 500 mil.'),
            (30_000_000, '€ 30,00 mi.'),
            (1_234_560_000, '€ 1.234,56 mi.'),
        ],
    )
    def test_uses_transfermarkt_brazilian_notation(self, euros, label):
        assert MarketDataset.format_euros(euros) == label
