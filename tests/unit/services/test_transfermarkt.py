from bot.domain.services.transfermarkt.parser import TransfermarktParser

_PLAYER_PAGE_HTML = """
<table class="items">
  <tr class="odd">
    <td>
      <table class="inline-table">
        <tr>
          <td class="hauptlink">
            <a href="/lionel-messi/profil/spieler/28003">Messi</a>
          </td>
          <td><img class="bilderrahmen-fixed" data-src="https://img.tm.com/portrait/small/28003.jpg"></td>
        </tr>
        <tr><td>Ponta Direita</td></tr>
      </table>
    </td>
    <td class="zentriert">36</td>
    <td class="zentriert">
      <img class="flaggenrahmen" title="Argentina" src="https://tmssl.akamaized.net/flags/arg.png">
    </td>
    <td class="zentriert">
      <a href="/inter-miami/startseite/verein/50251" title="Inter Miami">
        <img src="/wappen/verysmall/50251.png">
      </a>
    </td>
    <td class="rechts hauptlink">€ 20,00 mi.</td>
  </tr>
</table>
"""

_NO_CLUB_ROW_HTML = """
<table class="items">
  <tr class="odd">
    <td>
      <table class="inline-table">
        <tr>
          <td class="hauptlink"><a href="/p/profil/spieler/1">Solo Player</a></td>
          <td><img class="bilderrahmen-fixed" src="https://img.tm.com/portrait/small/1.jpg"></td>
        </tr>
        <tr><td>Goleiro</td></tr>
      </table>
    </td>
    <td class="zentriert">25</td>
    <td class="zentriert"><img class="flaggenrahmen" title="Brazil" src="..."></td>
    <td class="rechts hauptlink">€ 5,00 mi.</td>
  </tr>
</table>
"""

_SQUAD_VALUES_HTML = """
<table class="items">
  <tr class="odd">
    <td>
      <a href="/man-city/startseite/verein/281">Manchester City</a>
    </td>
    <td class="zentriert">30</td>
    <td class="zentriert">26,3</td>
    <td class="zentriert">18 (60%)</td>
    <td class="rechts">€ 1.200,00 mi.</td>
  </tr>
</table>
"""

_STANDINGS_HTML = """
<table class="items">
  <tbody>
    <tr>
      <td>1</td>
      <td><a href="/man-city/verein/281">Manchester City</a></td>
    </tr>
    <tr>
      <td>2</td>
      <td><a href="/arsenal/verein/11">Arsenal</a></td>
    </tr>
    <tr>
      <td>invalid</td>
      <td><a href="/some-club/verein/999">Some Club</a></td>
    </tr>
  </tbody>
</table>
"""

_CLUBS_PAGE_HTML = """
<table class="items">
  <tr class="odd">
    <td>
      <a href="/man-city/startseite/verein/281" title="Manchester City">Manchester City</a>
    </td>
    <td>
      <img class="flaggenrahmen" title="England">
    </td>
    <td>
      <a href="/premier-league/startseite/wettbewerb/GB1">Premier League</a>
    </td>
    <td class="rechts">€ 1.200,00 mi.</td>
  </tr>
</table>
"""

_PLAYER_PROFILE_HTML = """
<div class="info-table">
  <span class="info-table__content--regular">Altura:</span>
  <span class="info-table__content--bold">1,70 m</span>
  <span class="info-table__content--regular">Pé:</span>
  <span class="info-table__content--bold">esquerdo</span>
</div>
<div class="detail-position">
  <dt>Posições secundárias:</dt>
  <dd>Centroavante Meia Atacante</dd>
</div>
"""

_LEAGUE_CLUBS_HTML = """
<table class="items">
  <tr class="odd">
    <td><a href="/man-city/startseite/verein/281">Manchester City</a></td>
    <td class="rechts">€ 1.200,00 mi.</td>
  </tr>
  <tr class="even">
    <td><a href="/arsenal/startseite/verein/11">Arsenal</a></td>
    <td class="rechts">€ 900,00 mi.</td>
  </tr>
</table>
"""

_DUPLICATE_CLUBS_HTML = """
<table class="items">
  <tr class="odd">
    <td><a href="/man-city/startseite/verein/281">Manchester City</a></td>
    <td class="rechts">€ 1.200,00 mi.</td>
  </tr>
  <tr class="even">
    <td><a href="/man-city-b/startseite/verein/281">Man City Copy</a></td>
    <td class="rechts">€ 1.100,00 mi.</td>
  </tr>
</table>
"""


class TestParsePage:
    def test_returns_player_list(self):
        players = TransfermarktParser.parse_page(_PLAYER_PAGE_HTML)

        assert len(players) == 1
        p = players[0]
        assert p.name == 'Messi'
        assert p.position == 'Ponta Direita'
        assert p.age == 36
        assert p.nationality == 'Argentina'
        assert p.club == 'Inter Miami'
        assert p.club_id == '50251'
        assert p.market_value == '€ 20,00 mi.'

    def test_photo_url_upgraded_to_big_portrait(self):
        players = TransfermarktParser.parse_page(_PLAYER_PAGE_HTML)

        assert '/portrait/big/' in players[0].photo_url

    def test_badge_url_uses_akamaized_cdn(self):
        players = TransfermarktParser.parse_page(_PLAYER_PAGE_HTML)

        assert 'tmssl.akamaized.net' in players[0].badge_url
        assert '50251' in players[0].badge_url

    def test_profile_url_is_absolute(self):
        players = TransfermarktParser.parse_page(_PLAYER_PAGE_HTML)

        assert players[0].profile_url.startswith('https://')
        assert '28003' in players[0].profile_url

    def test_skips_row_without_club_by_default(self):
        players = TransfermarktParser.parse_page(_NO_CLUB_ROW_HTML)

        assert players == []

    def test_includes_row_without_club_when_require_club_false(self):
        players = TransfermarktParser.parse_page(_NO_CLUB_ROW_HTML, require_club=False)

        assert len(players) == 1
        assert players[0].name == 'Solo Player'

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_page('<div>no table</div>') == []


class TestParseSquadValues:
    def test_returns_stats_keyed_by_club_id(self):
        result = TransfermarktParser.parse_squad_values(_SQUAD_VALUES_HTML)

        assert '281' in result
        stats = result['281']
        assert stats.name == 'Manchester City'
        assert stats.club_id == '281'

    def test_extracts_squad_stats_fields(self):
        result = TransfermarktParser.parse_squad_values(_SQUAD_VALUES_HTML)

        stats = result['281']
        assert stats.squad_size == '30'
        assert stats.avg_age == '26,3'
        assert stats.foreigners_count == '18'
        assert stats.foreigners_pct == '60'

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_squad_values('<div>no table</div>') == {}


class TestParseTabelle:
    def test_returns_rank_keyed_by_club_id(self):
        result = TransfermarktParser.parse_tabelle(_STANDINGS_HTML)

        assert result == {'281': 1, '11': 2}

    def test_skips_rows_with_non_numeric_rank(self):
        result = TransfermarktParser.parse_tabelle(_STANDINGS_HTML)

        assert '999' not in result

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_tabelle('<div>no table</div>') == {}


class TestParseClubsPage:
    def test_returns_clubs_in_rank_order(self):
        clubs = TransfermarktParser.parse_clubs_page(_CLUBS_PAGE_HTML)

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
    def test_extracts_info_table_fields(self):
        info = TransfermarktParser.parse_player_profile(_PLAYER_PROFILE_HTML)

        assert info.get('Altura') == '1,70 m'
        assert info.get('Pé') == 'esquerdo'

    def test_extracts_detail_position_fields(self):
        info = TransfermarktParser.parse_player_profile(_PLAYER_PROFILE_HTML)

        assert info.get('Posições secundárias') == 'Centroavante Meia Atacante'

    def test_empty_html_returns_empty_dict(self):
        assert TransfermarktParser.parse_player_profile('<div>nothing</div>') == {}


class TestParseLeagueClubs:
    def test_returns_all_clubs(self):
        clubs = TransfermarktParser.parse_league_clubs(_LEAGUE_CLUBS_HTML)

        assert len(clubs) == 2
        assert clubs[0].name == 'Manchester City'
        assert clubs[0].club_id == '281'
        assert clubs[1].name == 'Arsenal'
        assert clubs[1].club_id == '11'

    def test_assigns_sequential_ranks(self):
        clubs = TransfermarktParser.parse_league_clubs(_LEAGUE_CLUBS_HTML)

        assert clubs[0].rank == 1
        assert clubs[1].rank == 2

    def test_badge_url_uses_cdn(self):
        clubs = TransfermarktParser.parse_league_clubs(_LEAGUE_CLUBS_HTML)

        assert 'tmssl.akamaized.net' in clubs[0].badge_url
        assert '281' in clubs[0].badge_url

    def test_deduplicates_clubs_by_id(self):
        clubs = TransfermarktParser.parse_league_clubs(_DUPLICATE_CLUBS_HTML)

        assert len(clubs) == 1
        assert clubs[0].name == 'Manchester City'

    def test_empty_html_returns_empty_list(self):
        assert TransfermarktParser.parse_league_clubs('<div>no table</div>') == []
