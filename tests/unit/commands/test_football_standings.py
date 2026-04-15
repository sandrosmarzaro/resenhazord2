import pytest

from bot.data.football import LEAGUES
from bot.data.football_zones import LEAGUE_ZONES
from bot.domain.commands.football_standings import FootballStandingsCommand
from bot.domain.models.football import TmStandingRow
from bot.domain.models.message import TextContent
from bot.domain.services.transfermarkt.service import TransfermarktService
from tests.factories.command_data import GroupCommandDataFactory

_LEAGUE = LEAGUES['br']
_ZONES = LEAGUE_ZONES['br']


def _make_standing(
    rank: int,
    team: str,
    points: int,
    goal_diff: int = 0,
) -> TmStandingRow:
    return TmStandingRow(
        rank=rank,
        team=team,
        matches=10,
        wins=6,
        draws=2,
        losses=2,
        goals_for=18,
        goals_against=10,
        goal_diff=goal_diff,
        points=points,
    )


_MOCK_STANDINGS = [
    _make_standing(1, 'Palmeiras', 26, goal_diff=11),
    _make_standing(2, 'Flamengo', 20, goal_diff=8),
    _make_standing(3, 'Sao Paulo', 20, goal_diff=6),
    _make_standing(4, 'Fluminense', 20, goal_diff=5),
    _make_standing(5, 'Bahia', 20, goal_diff=5),
    _make_standing(6, 'Botafogo', 18, goal_diff=3),
    _make_standing(7, 'Fortaleza', 17, goal_diff=2),
    _make_standing(8, 'Internacional', 16, goal_diff=1),
    _make_standing(9, 'Atletico-MG', 15, goal_diff=0),
    _make_standing(10, 'Corinthians', 14, goal_diff=-1),
    _make_standing(11, 'Vasco', 13, goal_diff=-2),
    _make_standing(12, 'Gremio', 12, goal_diff=-3),
    _make_standing(13, 'Santos', 11, goal_diff=-4),
    _make_standing(14, 'Cruzeiro', 10, goal_diff=-5),
    _make_standing(15, 'Athletico-PR', 10, goal_diff=-5),
    _make_standing(16, 'Juventude', 10, goal_diff=-6),
    _make_standing(17, 'Cuiaba', 9, goal_diff=-7),
    _make_standing(18, 'Vitoria', 8, goal_diff=-8),
    _make_standing(19, 'Criciuma', 7, goal_diff=-9),
    _make_standing(20, 'Atletico-GO', 6, goal_diff=-10),
]


@pytest.fixture
def command():
    return FootballStandingsCommand()


class TestConfig:
    def test_name(self, command):
        assert command.config.name == 'tabela'

    def test_alias(self, command):
        assert 'table' in command.config.aliases

    def test_category(self, command):
        from bot.domain.commands.base import Category

        assert command.config.category == Category.INFORMATION

    def test_platforms(self, command):
        from bot.domain.commands.base import Platform

        assert Platform.WHATSAPP in command.config.platforms
        assert Platform.DISCORD in command.config.platforms


class TestDefaultLiga:
    @pytest.mark.anyio
    async def test_defaults_to_brasileirao(self, command, mocker):
        mock_fetch = mocker.AsyncMock(return_value=_MOCK_STANDINGS)
        mocker.patch.object(TransfermarktService, 'fetch_full_standings', new=mock_fetch)

        data = GroupCommandDataFactory.build(text=',tabela')
        messages = await command.run(data)

        mock_fetch.assert_called_once_with(_LEAGUE)
        assert isinstance(messages[0].content, TextContent)


class TestFullTable:
    @pytest.mark.anyio
    async def test_returns_all_teams(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Palmeiras' in text
        assert 'Atletico-GO' in text

    @pytest.mark.anyio
    async def test_contains_league_name(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        assert _LEAGUE.name in messages[0].content.text

    @pytest.mark.anyio
    async def test_contains_points(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        assert '26 pts' in messages[0].content.text

    @pytest.mark.anyio
    async def test_shows_medal_emojis_for_top3(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        text = messages[0].content.text
        assert '🥇' in text
        assert '🥈' in text
        assert '🥉' in text

    @pytest.mark.anyio
    async def test_shows_zone_separators(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Sul-Americana' in text
        assert 'Rebaixamento' in text


class TestG4Flag:
    @pytest.mark.anyio
    async def test_filters_top_zone(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br g4')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Palmeiras' in text
        assert 'Botafogo' in text
        assert 'Fortaleza' not in text
        assert 'Atletico-GO' not in text


class TestZ4Flag:
    @pytest.mark.anyio
    async def test_filters_bottom_zone(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=_MOCK_STANDINGS),
        )

        data = GroupCommandDataFactory.build(text=',tabela br z4')
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Cuiaba' in text
        assert 'Atletico-GO' in text
        assert 'Palmeiras' not in text


class TestEmptyStandings:
    @pytest.mark.anyio
    async def test_returns_error(self, command, mocker):
        mocker.patch.object(
            TransfermarktService,
            'fetch_full_standings',
            new=mocker.AsyncMock(return_value=[]),
        )

        data = GroupCommandDataFactory.build(text=',tabela br')
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)


class TestFormatGoalDiff:
    def test_positive_goal_diff(self, command):
        standings = [_make_standing(1, 'Team', 20, goal_diff=5)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '+5' in result

    def test_negative_goal_diff(self, command):
        standings = [_make_standing(1, 'Team', 20, goal_diff=-3)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '-3' in result

    def test_zero_goal_diff(self, command):
        standings = [_make_standing(1, 'Team', 20, goal_diff=0)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '  0' in result


class TestZoneEmojis:
    def test_libertadores_zone_gets_green(self, command):
        standings = [_make_standing(4, 'Team', 20)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '🟢' in result

    def test_sulamericana_zone_gets_yellow(self, command):
        standings = [_make_standing(8, 'Team', 15)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '🟡' in result

    def test_relegation_zone_gets_red(self, command):
        standings = [_make_standing(18, 'Team', 8)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '🔴' in result

    def test_mid_table_gets_default(self, command):
        standings = [_make_standing(14, 'Team', 10)]

        result = command._format_table(standings, _LEAGUE, _ZONES)

        assert '⚪' in result
