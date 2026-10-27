import httpx
import pytest

from bot.data.football import LEAGUES, MARKET_LEAGUE_CODES
from bot.data.football_formations import FORMATIONS, specific_roles
from bot.domain.commands.football_team import FootballTeamCommand
from bot.domain.models.football import (
    FifaPlayer,
    SportsDBTeam,
    TmPlayer,
    TmSquadStats,
    TmStandingRow,
)
from bot.domain.models.message import ImageBufferContent, TextContent
from bot.domain.services.espn import EspnService
from bot.domain.services.fifa_ratings import FifaRatings
from bot.domain.services.market_dataset import MarketDataset
from bot.domain.services.team_caption_builder import TeamCaptionBuilder
from bot.domain.services.thesportsdb import TheSportsDBService
from bot.infrastructure.http_client import HttpClient
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

_LEAGUE = LEAGUES['pl']
_FORMATION = FORMATIONS[0]
_N_SLOTS = len(_FORMATION.slots)


def _make_squad_stats(
    club_id: str = '281', name: str = 'Manchester City Football Club', league_id: str = 'GB1'
) -> TmSquadStats:
    return TmSquadStats(
        market_value='€ 1.200,00 mi.',
        squad_size='30',
        avg_age='26,3',
        foreigners_count='18',
        foreigners_pct='60',
        club_id=club_id,
        name=name,
        badge_url=f'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png',
        league_id=league_id,
    )


def _make_sports_team(name: str = 'Manchester City') -> SportsDBTeam:
    return SportsDBTeam(
        name=name,
        country='England',
        founded='1880',
        badge_url='https://www.thesportsdb.com/images/media/team/badge/man-city.png',
        stadium='City of Manchester Stadium',
        capacity='55097',
    )


def _standing(rank: int, team: str) -> TmStandingRow:
    return TmStandingRow(
        rank=rank,
        team=team,
        matches=9,
        wins=7,
        draws=1,
        losses=1,
        goals_for=20,
        goals_against=8,
        goal_diff=12,
        points=22,
    )


_CITY = _make_squad_stats()
_CHELSEA = _make_squad_stats('631', 'Chelsea Football Club')
_AL_HILAL = _make_squad_stats('1114', 'Al-Hilal Saudi Football Club', league_id='SA1')


def _make_player(name: str, position: str) -> TmPlayer:
    return TmPlayer(
        name=name,
        position=position,
        age=25,
        nationality='Brazil',
        club='Manchester City',
        club_id='281',
        market_value=50_000_000,
        photo_url=f'https://img.a.transfermarkt.technology/portrait/header/{name}.jpg',
        badge_url='https://tmssl.akamaized.net/images/wappen/head/281.png',
        nationality_flag_emoji='🇧🇷',
    )


_MOCK_SQUAD = [
    _make_player('GK1', 'Goalkeeper'),
    _make_player('GK2', 'Goalkeeper'),
    _make_player('CB1', 'Centre-Back'),
    _make_player('CB2', 'Centre-Back'),
    _make_player('CB3', 'Centre-Back'),
    _make_player('LB1', 'Left-Back'),
    _make_player('RB1', 'Right-Back'),
    _make_player('DM1', 'Defensive Midfield'),
    _make_player('CM1', 'Central Midfield'),
    _make_player('CM2', 'Central Midfield'),
    _make_player('AM1', 'Attacking Midfield'),
    _make_player('LW1', 'Left Winger'),
    _make_player('RW1', 'Right Winger'),
    _make_player('ST1', 'Centre-Forward'),
]


@pytest.fixture
def command():
    return FootballTeamCommand()


@pytest.fixture
def badge(mocker):
    return mocker.patch.object(
        HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'fake-badge')
    )


@pytest.fixture
def pick_first(mocker):
    return mocker.patch(
        'bot.domain.commands.football_team.random.choice', side_effect=lambda pool: pool[0]
    )


@pytest.fixture
def sources(mocker, badge):
    clubs = mocker.AsyncMock(return_value=[_CITY, _CHELSEA])
    mocker.patch.object(MarketDataset, 'season', new=mocker.AsyncMock(return_value='2025/26'))
    mocker.patch.object(MarketDataset, 'clubs', new=clubs)
    mocker.patch.object(
        EspnService,
        'fetch_standings',
        new=mocker.AsyncMock(
            return_value=[_standing(1, 'Chelsea'), _standing(3, 'Manchester City')]
        ),
    )
    return clubs


@pytest.fixture
def search(mocker):
    return mocker.patch.object(
        TheSportsDBService,
        'search_team',
        new=mocker.AsyncMock(return_value=_make_sports_team()),
    )


async def _caption(command, text: str) -> str:
    messages = await command.run(GroupCommandDataFactory.build(text=text))
    return messages[0].content.caption


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (',time', True),
            (', time', True),
            (',TIME', True),
            (',time pl', True),
            (',time top10', True),
            (',time full', True),
            (',time pl top10 full', True),
            (',time show', True),
            (',time dm', True),
            (',time uy', False),
            ('time', False),
            (',timex', False),
            (',time hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestLeagueTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_caption_ranks_club_from_espn_table(self, command, sources, search, pick_first):
        caption = await _caption(command, ',time pl')

        assert caption.splitlines()[0] == '*Manchester City* — Premier League'
        assert '📊 3º na tabela' in caption
        assert caption.splitlines()[-2:] == ['💰 € 1.200,00 mi.', '📅 Valores da temporada 2025/26']

    @pytest.mark.anyio
    async def test_searches_details_by_espn_short_name(self, command, sources, search, pick_first):
        caption = await _caption(command, ',time pl')

        search.assert_awaited_once_with('Manchester City')
        assert '🏟️ City of Manchester Stadium' in caption

    @pytest.mark.anyio
    async def test_failed_details_search_keeps_dataset_name(self, command, sources, mocker):
        mocker.patch.object(
            TheSportsDBService,
            'search_team',
            new=mocker.AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    '429', request=httpx.Request('GET', 'https://x'), response=httpx.Response(429)
                )
            ),
        )
        mocker.patch(
            'bot.domain.commands.football_team.random.choice', side_effect=lambda pool: pool[0]
        )

        caption = await _caption(command, ',time pl')

        assert caption.splitlines()[0] == f'*{_CITY.name}* — Premier League'

    @pytest.mark.anyio
    async def test_sends_club_badge(self, command, sources, search, pick_first, badge):
        messages = await command.run(GroupCommandDataFactory.build(text=',time pl'))

        assert isinstance(messages[0].content, ImageBufferContent)
        badge.assert_awaited_once_with(_CITY.badge_url)

    @pytest.mark.anyio
    async def test_random_league_comes_from_market_leagues(
        self, command, sources, search, pick_first
    ):
        await command.run(GroupCommandDataFactory.build(text=',time'))

        sources.assert_awaited_once_with(LEAGUES[MARKET_LEAGUE_CODES[0]].tm_id)

    @pytest.mark.anyio
    async def test_top_n_keeps_clubs_ranked_inside_it(self, command, sources, search, pick_first):
        await command.run(GroupCommandDataFactory.build(text=',time pl top2'))

        pick_first.assert_called_once_with([_CHELSEA])

    @pytest.mark.anyio
    async def test_top_n_without_ranked_clubs_keeps_all(self, command, sources, search, mocker):
        mocker.patch.object(EspnService, 'fetch_standings', new=mocker.AsyncMock(return_value=[]))
        pick = mocker.patch(
            'bot.domain.commands.football_team.random.choice', side_effect=lambda pool: pool[0]
        )

        caption = await _caption(command, ',time pl top2')

        pick.assert_called_once_with([_CITY, _CHELSEA])
        assert 'tabela' not in caption

    @pytest.mark.anyio
    async def test_no_clubs_replies_with_text(self, command, sources, search):
        sources.return_value = []

        messages = await command.run(GroupCommandDataFactory.build(text=',time pl'))

        assert isinstance(messages[0].content, TextContent)

    @pytest.mark.anyio
    async def test_view_once_by_default(self, command, sources, search, pick_first):
        messages = await command.run(GroupCommandDataFactory.build(text=',time pl'))

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, sources, search, pick_first):
        messages = await command.run(GroupCommandDataFactory.build(text=',time pl show'))

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_to_participant(self, command, sources, search, pick_first):
        data = GroupCommandDataFactory.build(text=',time pl dm')

        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_private_keeps_jid(self, command, sources, search, pick_first):
        data = PrivateCommandDataFactory.build(text=',time pl dm')

        messages = await command.run(data)

        assert messages[0].jid == data.jid


class TestGlobalTopTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_picks_among_most_valuable_clubs(self, command, sources, search, pick_first):
        sources.return_value = [_CITY, _CHELSEA, _AL_HILAL]

        caption = await _caption(command, ',time top2')

        pick_first.assert_called_once_with([_CITY, _CHELSEA])
        assert '🏆 #1º mais valioso do mundo' in caption
        assert '📊 3º na tabela' in caption

    @pytest.mark.anyio
    async def test_club_outside_known_leagues_gets_world_caption(self, command, sources, mocker):
        sources.return_value = [_AL_HILAL]
        search = mocker.patch.object(
            TheSportsDBService,
            'search_team',
            new=mocker.AsyncMock(return_value=_make_sports_team('Al-Hilal')),
        )

        caption = await _caption(command, ',time top1')

        search.assert_awaited_once_with(_AL_HILAL.name)
        assert caption.splitlines()[:3] == ['*Al-Hilal*', '', '🌍 England   📅 1880']
        assert '🏆 #1º mais valioso do mundo' in caption


class TestFullTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def squad(self, mocker, badge):
        fetch = mocker.AsyncMock(return_value=_MOCK_SQUAD)
        mocker.patch.object(MarketDataset, 'season', new=mocker.AsyncMock(return_value='2025/26'))
        mocker.patch.object(MarketDataset, 'players', new=fetch)
        mocker.patch('bot.domain.commands.football_team.random_formation', return_value=_FORMATION)
        return fetch

    @pytest.fixture
    def field(self, mocker):
        return mocker.patch(
            'bot.domain.services.full_lineup_builder.build_football_field',
            return_value=b'fake-field-image',
        )

    @staticmethod
    def _names(field) -> list[str]:
        return field.call_args.args[1]

    @pytest.mark.anyio
    async def test_league_lineup_uses_league_players(self, command, squad, field):
        messages = await command.run(GroupCommandDataFactory.build(text=',time pl full'))

        squad.assert_awaited_once_with('GB1')
        assert isinstance(messages[0].content, ImageBufferContent)
        assert messages[0].content.caption == (
            f'⚽ *Escalação Aleatória* — {_FORMATION.name}\n💰 € {50 * _N_SLOTS},00 mi.\n'
            '📅 Valores da temporada 2025/26'
        )

    @pytest.mark.anyio
    async def test_global_lineup_fills_every_slot(self, command, squad, field):
        await command.run(GroupCommandDataFactory.build(text=',time full'))

        squad.assert_awaited_once_with('')
        assert len(self._names(field)) == _N_SLOTS
        assert all(self._names(field))

    @pytest.mark.anyio
    async def test_top_n_keeps_the_most_valuable_per_role(self, command, squad, field):
        await command.run(GroupCommandDataFactory.build(text=',time top1 full'))

        assert ('GK1' in self._names(field), 'GK2' in self._names(field)) == (True, False)

    @pytest.mark.anyio
    async def test_fetches_photos_without_transfermarkt_headers(self, command, squad, field, badge):
        await command.run(GroupCommandDataFactory.build(text=',time top1 full'))

        badge.assert_any_await('https://img.a.transfermarkt.technology/portrait/header/GK1.jpg')


def _fifa_player(name: str, overall: int) -> FifaPlayer:
    return FifaPlayer(
        name=name,
        overall=overall,
        photo_url=f'https://ratings-images-prod.pulse.ea.com/{name}.png',
        badge_url='https://drop-assets.ea.com/images/crest.png',
        nationality_flag_emoji='🇧🇷',
    )


class TestFifaTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.fixture
    def ratings(self, mocker, badge):
        roles = set(specific_roles(_FORMATION))
        pools = {
            role: [_fifa_player(f'{role}-best', 90)]
            + [_fifa_player(f'{role}-{i}', 80) for i in range(4)]
            for role in roles
        }
        fetch = mocker.AsyncMock(return_value=pools)
        mocker.patch.object(FifaRatings, 'role_pools', new=fetch)
        mocker.patch('bot.domain.commands.football_team.random_formation', return_value=_FORMATION)
        return fetch

    @pytest.fixture
    def field(self, mocker):
        return mocker.patch(
            'bot.domain.services.full_lineup_builder.build_football_field',
            return_value=b'fake-field-image',
        )

    @pytest.mark.anyio
    async def test_top1_fields_the_best_of_each_role(self, command, ratings, field):
        messages = await command.run(GroupCommandDataFactory.build(text=',time fifa top1'))

        ratings.assert_awaited_once_with(set(specific_roles(_FORMATION)))
        assert messages[0].content.caption == (
            f'⚽ *Escalação FIFA* — {_FORMATION.name}\n⭐ Overall médio: 90'
        )
        assert field.call_args.args[4] == 'OVR médio 90'

    @pytest.mark.anyio
    async def test_fills_every_slot(self, command, ratings, field):
        messages = await command.run(GroupCommandDataFactory.build(text=',time fifa'))

        names = field.call_args.args[1]
        assert isinstance(messages[0].content, ImageBufferContent)
        assert (len(names), all(names)) == (_N_SLOTS, True)

    @pytest.mark.anyio
    async def test_league_filter_is_not_supported(self, command, ratings):
        messages = await command.run(GroupCommandDataFactory.build(text=',time pl fifa'))

        assert isinstance(messages[0].content, TextContent)
        ratings.assert_not_awaited()


class TestBuildTeamCaption:
    def test_includes_team_and_league(self):
        caption = TeamCaptionBuilder.build(_CITY, _make_sports_team(), _LEAGUE, rank=1)

        assert caption.splitlines()[0] == '*Manchester City* — Premier League'

    def test_falls_back_to_dataset_name_without_sports_team(self):
        caption = TeamCaptionBuilder.build(_CITY, None, _LEAGUE, rank=None)

        assert caption.splitlines()[0] == f'*{_CITY.name}* — Premier League'

    def test_includes_stadium_when_sports_team_provided(self):
        caption = TeamCaptionBuilder.build(_CITY, _make_sports_team(), _LEAGUE, rank=None)

        assert '🏟️ City of Manchester Stadium' in caption

    def test_no_rank_line_when_rank_is_none(self):
        caption = TeamCaptionBuilder.build(_CITY, None, _LEAGUE, rank=None)

        assert 'tabela' not in caption

    def test_without_league_or_sports_team_shows_only_world_flag(self):
        caption = TeamCaptionBuilder.build(_AL_HILAL, None, None, rank=None, global_rank=7)

        assert caption.splitlines()[:3] == [f'*{_AL_HILAL.name}*', '', '🌍']


class TestFormatHeadLine:
    def test_includes_flag_and_country(self):
        result = TeamCaptionBuilder._head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '')

        assert '🏴󠁧󠁢󠁥󠁮󠁧󠁿' in result
        assert 'England' in result

    def test_includes_founded_when_provided(self):
        result = TeamCaptionBuilder._head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '1992')

        assert '1992' in result

    def test_omits_country_when_empty(self):
        result = TeamCaptionBuilder._head_line('🌍', '', '')

        assert result == '\n🌍'

    def test_no_founded_when_empty(self):
        result = TeamCaptionBuilder._head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '')

        assert '📅' not in result
