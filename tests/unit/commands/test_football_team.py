import pytest

from bot.data.football import LEAGUES
from bot.data.football_formations import FORMATIONS
from bot.domain.commands.football_team import FootballTeamCommand
from bot.domain.models.football import SportsDBTeam, TmClub, TmPlayer, TmSquadStats
from bot.domain.models.message import ImageBufferContent
from bot.domain.services.thesportsdb import TheSportsDBService
from bot.domain.services.transfermarkt import TransfermarktService
from bot.infrastructure.http_client import HttpClient
from tests.factories.command_data import GroupCommandDataFactory, PrivateCommandDataFactory

_LEAGUE = LEAGUES['pl']
_FORMATION = FORMATIONS[0]
_N_SLOTS = len(_FORMATION.slots)


def _make_squad_stats(club_id: str = '281', name: str = 'Manchester City') -> TmSquadStats:
    return TmSquadStats(
        market_value='€ 1.200,00 mi.',
        squad_size='30',
        avg_age='26,3',
        foreigners_count='18',
        foreigners_pct='60',
        club_id=club_id,
        name=name,
        badge_url=f'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png',
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


def _make_tm_club(club_id: str = '281', league_tm_id: str = 'GB1') -> TmClub:
    return TmClub(
        rank=1,
        name='Manchester City',
        country='England',
        squad_value='€ 1.200,00 mi.',
        club_id=club_id,
        badge_url=f'https://tmssl.akamaized.net/images/wappen/head/{club_id}.png',
        league_tm_id=league_tm_id,
    )


def _make_player(name: str, position: str) -> TmPlayer:
    return TmPlayer(
        name=name,
        position=position,
        age=25,
        nationality='Brazil',
        club='Manchester City',
        club_id='281',
        market_value='€ 50,00 mi.',
        photo_url='',
        badge_url='',
        nationality_flag_emoji='🇧🇷',
    )


_MOCK_SQUAD = [
    _make_player('GK1', 'Goleiro'),
    _make_player('CB1', 'Zagueiro'),
    _make_player('CB2', 'Zagueiro'),
    _make_player('CB3', 'Zagueiro'),
    _make_player('LB1', 'Lateral Esq.'),
    _make_player('RB1', 'Lateral Dir.'),
    _make_player('CM1', 'Meia-Central'),
    _make_player('CM2', 'Meia-Central'),
    _make_player('CM3', 'Meia-Central'),
    _make_player('CM4', 'Meia-Central'),
    _make_player('LW1', 'Ponta Esquerda'),
    _make_player('ST1', 'Centroavante'),
    _make_player('RW1', 'Ponta Direita'),
    _make_player('AM1', 'Meia Ofensivo'),
    _make_player('DM1', 'Volante'),
]


@pytest.fixture
def command():
    return FootballTeamCommand()


@pytest.fixture
def mock_league_services(mocker):
    mocker.patch.object(
        TransfermarktService,
        'fetch_squad_values',
        new=mocker.AsyncMock(return_value={'281': _make_squad_stats()}),
    )
    mocker.patch.object(
        TransfermarktService,
        'fetch_standings',
        new=mocker.AsyncMock(return_value={'281': 1}),
    )
    mocker.patch.object(
        TheSportsDBService,
        'get_teams',
        new=mocker.AsyncMock(return_value=[_make_sports_team()]),
    )
    mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'fake-badge'))
    # random.choice is called twice: once for LEAGUE_CODES (returns str), once for clubs list
    _stats = _make_squad_stats()
    mocker.patch(
        'bot.domain.commands.football_team.random.choice',
        side_effect=lambda seq: 'pl' if seq and isinstance(seq[0], str) else _stats,
    )


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
            ('time', False),
            (',timex', False),
            (',time hello', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRandomTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_single_image(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_team_info(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Manchester City' in caption

    @pytest.mark.anyio
    async def test_caption_contains_league_rank(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time')
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '1º' in caption

    @pytest.mark.anyio
    async def test_view_once_by_default(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time')
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time show')
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_to_participant(self, command, mock_league_services):
        data = GroupCommandDataFactory.build(text=',time dm')
        messages = await command.run(data)

        assert messages[0].jid == data.participant

    @pytest.mark.anyio
    async def test_dm_flag_private_keeps_jid(self, command, mock_league_services):
        data = PrivateCommandDataFactory.build(text=',time dm')
        messages = await command.run(data)

        assert messages[0].jid == data.jid

    @pytest.mark.anyio
    async def test_empty_squad_returns_error_text(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_squad_values',
            new=mocker.AsyncMock(return_value={}),
        )
        mocker.patch.object(
            TransfermarktService, 'fetch_standings', new=mocker.AsyncMock(return_value={})
        )
        mocker.patch.object(TheSportsDBService, 'get_teams', new=mocker.AsyncMock(return_value=[]))

        data = GroupCommandDataFactory.build(text=',time')
        messages = await command.run(data)

        from bot.domain.models.message import TextContent

        assert isinstance(messages[0].content, TextContent)


class TestRandomTeamWithLiga:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_passes_league_to_services(self, command, mocker):
        mock_fetch_squad = mocker.AsyncMock(return_value={'281': _make_squad_stats()})
        mocker.patch.object(TransfermarktService, 'fetch_squad_values', new=mock_fetch_squad)
        mocker.patch.object(
            TransfermarktService,
            'fetch_standings',
            new=mocker.AsyncMock(return_value={'281': 1}),
        )
        mocker.patch.object(
            TheSportsDBService,
            'get_teams',
            new=mocker.AsyncMock(return_value=[_make_sports_team()]),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))
        mocker.patch(
            'bot.domain.commands.football_team.random.choice', return_value=_make_squad_stats()
        )

        data = GroupCommandDataFactory.build(text=',time pl')
        await command.run(data)

        mock_fetch_squad.assert_called_once_with(_LEAGUE)


class TestGlobalTopTeam:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_image_when_league_found(self, command, mocker):
        top_club = _make_tm_club(league_tm_id='GB1')
        mocker.patch.object(
            TransfermarktService,
            'fetch_top_clubs',
            new=mocker.AsyncMock(return_value=[top_club]),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_squad_values',
            new=mocker.AsyncMock(return_value={'281': _make_squad_stats()}),
        )
        mocker.patch.object(
            TransfermarktService,
            'fetch_standings',
            new=mocker.AsyncMock(return_value={'281': 1}),
        )
        mocker.patch.object(
            TheSportsDBService,
            'get_teams',
            new=mocker.AsyncMock(return_value=[_make_sports_team()]),
        )
        mocker.patch.object(HttpClient, 'get_buffer', new=mocker.AsyncMock(return_value=b'img'))
        mocker.patch('bot.domain.commands.football_team.random.choice', return_value=top_club)

        data = GroupCommandDataFactory.build(text=',time top5')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_when_no_clubs(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_top_clubs',
            new=mocker.AsyncMock(return_value=[]),
        )

        data = GroupCommandDataFactory.build(text=',time top5')
        messages = await command.run(data)

        from bot.domain.models.message import TextContent

        assert isinstance(messages[0].content, TextContent)


class TestFullTeamWithLiga:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_field_image(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_league_full_squad',
            new=mocker.AsyncMock(return_value=_MOCK_SQUAD),
        )
        mocker.patch(
            'bot.domain.commands.football_team.build_football_field',
            return_value=b'fake-field-image',
        )
        mocker.patch(
            'bot.domain.commands.football_team.random_formation',
            return_value=_FORMATION,
        )

        data = GroupCommandDataFactory.build(text=',time pl full')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_caption_contains_formation_name(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_league_full_squad',
            new=mocker.AsyncMock(return_value=_MOCK_SQUAD),
        )
        mocker.patch(
            'bot.domain.commands.football_team.build_football_field',
            return_value=b'fake-field-image',
        )
        mocker.patch(
            'bot.domain.commands.football_team.random_formation',
            return_value=_FORMATION,
        )

        data = GroupCommandDataFactory.build(text=',time pl full')
        messages = await command.run(data)

        assert _FORMATION.name in messages[0].content.caption


class TestFullTeamGlobal:
    @pytest.fixture
    def anyio_backend(self):
        return 'asyncio'

    @pytest.mark.anyio
    async def test_returns_field_image(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_by_specific_position',
            new=mocker.AsyncMock(return_value=_MOCK_SQUAD[:3]),
        )
        mocker.patch(
            'bot.domain.commands.football_team.build_football_field',
            return_value=b'fake-field-image',
        )
        mocker.patch(
            'bot.domain.commands.football_team.random_formation',
            return_value=_FORMATION,
        )

        data = GroupCommandDataFactory.build(text=',time full')
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)


class TestBuildTeamCaption:
    def test_includes_team_and_league(self):
        club = _make_squad_stats()
        sports_team = _make_sports_team()

        caption = FootballTeamCommand._build_team_caption(club, sports_team, _LEAGUE, rank=1)

        assert 'Manchester City' in caption
        assert _LEAGUE.name in caption

    def test_includes_rank_when_provided(self):
        club = _make_squad_stats()

        caption = FootballTeamCommand._build_team_caption(club, None, _LEAGUE, rank=3)

        assert '3º' in caption

    def test_includes_global_rank_when_provided(self):
        club = _make_squad_stats()

        caption = FootballTeamCommand._build_team_caption(
            club, None, _LEAGUE, rank=None, global_rank=5
        )

        assert '#5' in caption

    def test_includes_stadium_when_sports_team_provided(self):
        club = _make_squad_stats()
        sports_team = _make_sports_team()

        caption = FootballTeamCommand._build_team_caption(club, sports_team, _LEAGUE, rank=None)

        assert 'City of Manchester Stadium' in caption

    def test_no_rank_line_when_rank_is_none(self):
        club = _make_squad_stats()

        caption = FootballTeamCommand._build_team_caption(club, None, _LEAGUE, rank=None)

        assert 'tabela' not in caption


class TestFormatHeadLine:
    def test_includes_flag_and_country(self):
        result = FootballTeamCommand._format_head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '')

        assert '🏴󠁧󠁢󠁥󠁮󠁧󠁿' in result
        assert 'England' in result

    def test_includes_founded_when_provided(self):
        result = FootballTeamCommand._format_head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '1992')

        assert '1992' in result

    def test_omits_country_when_empty(self):
        result = FootballTeamCommand._format_head_line('🌍', '', '')

        assert result == '\n🌍'

    def test_no_founded_when_empty(self):
        result = FootballTeamCommand._format_head_line('🏴󠁧󠁢󠁥󠁮󠁧󠁿', 'England', '')

        assert '📅' not in result
