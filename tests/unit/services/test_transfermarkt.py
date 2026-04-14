from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from bot.domain.services.transfermarkt.client import TransfermarktClient
from bot.domain.services.transfermarkt.parser import TransfermarktParser

_HTML_DIR = Path(__file__).resolve().parent.parent.parent / 'fixtures' / 'html'


def _load_html(name: str) -> str:
    return (_HTML_DIR / name).read_text()


@pytest.fixture
def player_page_html() -> str:
    return _load_html('player_page.html')


@pytest.fixture
def no_club_row_html() -> str:
    return _load_html('no_club_row.html')


@pytest.fixture
def squad_values_html() -> str:
    return _load_html('squad_values.html')


@pytest.fixture
def standings_html() -> str:
    return _load_html('standings.html')


@pytest.fixture
def clubs_page_html() -> str:
    return _load_html('clubs_page.html')


@pytest.fixture
def player_profile_html() -> str:
    return _load_html('player_profile.html')


@pytest.fixture
def league_clubs_html() -> str:
    return _load_html('league_clubs.html')


@pytest.fixture
def duplicate_clubs_html() -> str:
    return _load_html('duplicate_clubs.html')


class TestParsePage:
    def test_returns_player_list(self, player_page_html):
        players = TransfermarktParser.parse_page(player_page_html)

        assert len(players) == 1
        p = players[0]
        assert p.name == 'Messi'
        assert p.position == 'Ponta Direita'
        assert p.age == 36
        assert p.nationality == 'Argentina'
        assert p.club == 'Inter Miami'
        assert p.club_id == '50251'
        assert p.market_value == '€ 20,00 mi.'

    def test_photo_url_upgraded_to_big_portrait(self, player_page_html):
        players = TransfermarktParser.parse_page(player_page_html)

        assert '/portrait/big/' in players[0].photo_url

    def test_badge_url_uses_akamaized_cdn(self, player_page_html):
        players = TransfermarktParser.parse_page(player_page_html)

        assert 'tmssl.akamaized.net' in players[0].badge_url
        assert '50251' in players[0].badge_url

    def test_profile_url_is_absolute(self, player_page_html):
        players = TransfermarktParser.parse_page(player_page_html)

        assert players[0].profile_url.startswith('https://')
        assert '28003' in players[0].profile_url

    def test_skips_row_without_club_by_default(self, no_club_row_html):
        players = TransfermarktParser.parse_page(no_club_row_html)

        assert players == []

    def test_includes_row_without_club_when_require_club_false(self, no_club_row_html):
        players = TransfermarktParser.parse_page(no_club_row_html, require_club=False)

        assert len(players) == 1
        assert players[0].name == 'Solo Player'

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_page('<div>no table</div>') == []


class TestParseSquadValues:
    def test_returns_stats_keyed_by_club_id(self, squad_values_html):
        result = TransfermarktParser.parse_squad_values(squad_values_html)

        assert '281' in result
        stats = result['281']
        assert stats.name == 'Manchester City'
        assert stats.club_id == '281'

    def test_extracts_squad_stats_fields(self, squad_values_html):
        result = TransfermarktParser.parse_squad_values(squad_values_html)

        stats = result['281']
        assert stats.squad_size == '30'
        assert stats.avg_age == '26,3'
        assert stats.foreigners_count == '18'
        assert stats.foreigners_pct == '60'

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_squad_values('<div>no table</div>') == {}


class TestParseTabelle:
    def test_returns_rank_keyed_by_club_id(self, standings_html):
        result = TransfermarktParser.parse_tabelle(standings_html)

        assert result == {'281': 1, '11': 2}

    def test_skips_rows_with_non_numeric_rank(self, standings_html):
        result = TransfermarktParser.parse_tabelle(standings_html)

        assert '999' not in result

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_tabelle('<div>no table</div>') == {}


@pytest.fixture
def full_standings_html() -> str:
    return _load_html('full_standings.html')


class TestParseFullTabelle:
    def test_returns_full_standing_rows(self, full_standings_html):
        result = TransfermarktParser.parse_full_tabelle(full_standings_html)

        assert len(result) == 3
        first = result[0]
        assert first.rank == 1
        assert first.team == 'Palmeiras'
        assert first.matches == 11
        assert first.wins == 8
        assert first.draws == 2
        assert first.losses == 1
        assert first.goals_for == 21
        assert first.goals_against == 10
        assert first.goal_diff == 11
        assert first.points == 26

    def test_parses_negative_goal_difference(self, full_standings_html):
        result = TransfermarktParser.parse_full_tabelle(full_standings_html)

        cuiaba = result[2]
        assert cuiaba.goal_diff == -7

    def test_skips_rows_with_non_numeric_rank(self, full_standings_html):
        result = TransfermarktParser.parse_full_tabelle(full_standings_html)

        teams = [r.team for r in result]
        assert 'Bad Club' not in teams

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_full_tabelle('<div>no table</div>') == []


class TestParseClubsPage:
    def test_returns_clubs_in_rank_order(self, clubs_page_html):
        clubs = TransfermarktParser.parse_clubs_page(clubs_page_html)

        assert len(clubs) == 1
        club = clubs[0]
        assert club.rank == 1
        assert club.name == 'Manchester City'
        assert club.country == 'England'
        assert club.club_id == '281'
        assert club.league_tm_id == 'GB1'
        assert 'tmssl.akamaized.net' in club.badge_url

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_clubs_page('<div>no table</div>') == []


class TestParsePlayerProfile:
    def test_extracts_info_table_fields(self, player_profile_html):
        info = TransfermarktParser.parse_player_profile(player_profile_html)

        assert info.get('Altura') == '1,70 m'
        assert info.get('Pé') == 'esquerdo'

    def test_extracts_detail_position_fields(self, player_profile_html):
        info = TransfermarktParser.parse_player_profile(player_profile_html)

        assert info.get('Posições secundárias') == 'Centroavante Meia Atacante'

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_player_profile('<div>nothing</div>') == {}


class TestParseLeagueClubs:
    def test_returns_all_clubs(self, league_clubs_html):
        clubs = TransfermarktParser.parse_league_clubs(league_clubs_html)

        assert len(clubs) == 2
        assert clubs[0].name == 'Manchester City'
        assert clubs[0].club_id == '281'
        assert clubs[1].name == 'Arsenal'
        assert clubs[1].club_id == '11'

    def test_assigns_sequential_ranks(self, league_clubs_html):
        clubs = TransfermarktParser.parse_league_clubs(league_clubs_html)

        assert clubs[0].rank == 1
        assert clubs[1].rank == 2

    def test_badge_url_uses_cdn(self, league_clubs_html):
        clubs = TransfermarktParser.parse_league_clubs(league_clubs_html)

        assert 'tmssl.akamaized.net' in clubs[0].badge_url
        assert '281' in clubs[0].badge_url

    def test_deduplicates_clubs_by_id(self, duplicate_clubs_html):
        clubs = TransfermarktParser.parse_league_clubs(duplicate_clubs_html)

        assert len(clubs) == 1
        assert clubs[0].name == 'Manchester City'

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_league_clubs('<div>no table</div>') == []


@pytest.fixture
def live_matches_html() -> str:
    return _load_html('live_matches.html')


class TestParseLiveMatches:
    def test_returns_matches_from_all_competitions(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        assert len(matches) == 4
        comps = {m.competition_name for m in matches}
        assert 'Brasileirão' in comps
        assert 'Premier League' in comps

    def test_extracts_live_match_scores(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        flamengo = next(m for m in matches if m.home_team == 'Flamengo')
        assert flamengo.home_score == 2
        assert flamengo.away_score == 1
        assert flamengo.status.value == 'live'

    def test_extracts_not_started_match(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        botafogo = next(m for m in matches if m.home_team == 'Botafogo')
        assert botafogo.home_score is None
        assert botafogo.away_score is None
        assert botafogo.status.value == 'notstarted'

    def test_extracts_match_time(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        flamengo = next(m for m in matches if m.home_team == 'Flamengo')
        assert flamengo.match_time == "67'"

    def test_extracts_scheduled_time(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        botafogo = next(m for m in matches if m.home_team == 'Botafogo')
        assert botafogo.match_time == '15:00'

    def test_extracts_country_and_flag(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        brasileiro = next(m for m in matches if m.competition_name == 'Brasileirão')
        assert brasileiro.country == 'Brasil'
        assert brasileiro.country_flag_emoji == '🇧🇷'

    def test_extracts_match_id(self, live_matches_html):
        matches = TransfermarktParser.parse_live_matches(live_matches_html)

        flamengo = next(m for m in matches if m.home_team == 'Flamengo')
        assert flamengo.match_id == '4814374'

    def test_deduplicates_duplicate_matches(self):
        html = """
        <div class="live-block">
            <h2>
                <img class="wettbewerblogo" title="Brasil">
                <a href="/brasileirao/startseite/wettbewerb/BR1">Brasileirão</a>
            </h2>
            <table class="livescore">
                <tr>
                    <td class="club verein-heim"><a href="#">Time A</a></td>
                    <td class="ergebnis">
                        <a href="/spielbericht/123">
                            <span class="matchresult">1 - 0</span>
                        </a>
                    </td>
                    <td class="club verein-gast"><a href="#">Time B</a></td>
                </tr>
                <tr>
                    <td class="club verein-heim"><a href="#">Time A</a></td>
                    <td class="ergebnis">
                        <a href="/spielbericht/123">
                            <span class="matchresult">1 - 0</span>
                        </a>
                    </td>
                    <td class="club verein-gast"><a href="#">Time B</a></td>
                </tr>
            </table>
        </div>
        """
        matches = TransfermarktParser.parse_live_matches(html)

        assert len(matches) == 1

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_live_matches('<div>no matches</div>') == []

    def test_no_live_blocks_returns_empty_list(self):
        html = '<div class="other">Some other content</div>'
        assert TransfermarktParser.parse_live_matches(html) == []


class TestFetchLiveMatchesUrl:
    @pytest.mark.anyio
    async def test_fetch_live_matches_uses_br_yesterday_and_today_dates(self):
        from datetime import timedelta, timezone

        br_time = timezone(timedelta(hours=-3))
        today = datetime.now(br_time).date()
        yesterday = today - timedelta(days=1)

        with patch(
            'bot.infrastructure.http_client.HttpClient.get',
            new_callable=AsyncMock,
        ) as mock_get:
            mock_response = AsyncMock()
            mock_response.text = '<div class="live-block"></div>'
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            await TransfermarktClient.fetch_live_matches()

            assert mock_get.call_count == 2
            urls = [call.args[0] for call in mock_get.call_args_list]
            assert any(f'datum={yesterday.strftime("%Y-%m-%d")}' in u for u in urls)
            assert any(f'datum={today.strftime("%Y-%m-%d")}' in u for u in urls)
            for url in urls:
                assert 'transfermarkt.com.br/live/index' in url

    @pytest.mark.anyio
    async def test_fetch_live_matches_dedupes_by_match_id(self):
        shared_html = """
        <div class="live-block">
          <h2><a href="/wettbewerb/BR1">Brasileirão</a></h2>
          <table class="livescore">
            <tr>
              <td class="verein-heim"><a>Flamengo</a></td>
              <td class="ergebnis"><a title="Ao vivo" href="/spielbericht/9999">1:0</a></td>
              <td class="verein-gast"><a>Palmeiras</a></td>
            </tr>
          </table>
        </div>
        """
        with patch(
            'bot.infrastructure.http_client.HttpClient.get',
            new_callable=AsyncMock,
        ) as mock_get:
            mock_response = AsyncMock()
            mock_response.text = shared_html
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            result = await TransfermarktClient.fetch_live_matches()

            assert len(result) == 1
            assert result[0].match_id == '9999'
