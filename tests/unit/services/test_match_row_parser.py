from bs4 import BeautifulSoup

from bot.domain.services.transfermarkt.match_row_parser import CompetitionContext, MatchRowParser


def _make_html_table(rows_html: str) -> str:
    return f'<table>{rows_html}</table>'


def _match_row(
    home: str = 'Home',
    away: str = 'Away',
    score: str = '2:1',
    match_id: str = '123',
) -> str:
    return (
        f'<tr>'
        f'<td class="verein-heim"><a>{home}</a></td>'
        f'<td class="verein-gast"><a>{away}</a></td>'
        f'<td class="ergebnis"><a href="/matches/{match_id}">{score}</a></td>'
        f'</tr>'
    )


class TestParseLiveTableRows:
    def test_parses_valid_row(self):
        ctx = CompetitionContext(name='Brasileirão', code='BRA1', country='Brasil', flag_emoji='🇧🇷')
        html = _make_html_table(_match_row('Flamengo', 'Palmeiras'))
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        assert table is not None

        matches = MatchRowParser.parse_live_table_rows(table, ctx)

        assert len(matches) == 1
        assert matches[0].home_team == 'Flamengo'
        assert matches[0].away_team == 'Palmeiras'
        assert matches[0].competition_code == 'BRA1'

    def test_skips_row_without_result_cell(self):
        ctx = CompetitionContext(name='Brasileirão', code='BRA1', country='Brasil', flag_emoji='🇧🇷')
        html = _make_html_table('<tr><td class="verein-heim"><a>Home</a></td></tr>')
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        assert table is not None

        matches = MatchRowParser.parse_live_table_rows(table, ctx)

        assert matches == []

    def test_extract_round_returns_none_when_absent(self):
        html = '<tr><td></td></tr>'
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')
        assert row is not None

        assert MatchRowParser._extract_round(row) is None
