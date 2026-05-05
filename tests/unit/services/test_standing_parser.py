from bot.domain.services.transfermarkt.standing_parser import StandingParser


def _standing_table_html(rows: str) -> str:
    return f'<table class="items"><tbody>{rows}</tbody></table>'


def _standing_row_html(rank: int, team: str, club_id: str = '281') -> str:
    return (
        f'<tr>'
        f'<td>{rank}</td>'
        f'<td class="no-border-links"><a href="/verein/{club_id}/">{team}</a></td>'
        f'<td class="zentriert">{rank}</td>'
        f'<td class="zentriert">{rank - 1}</td>'
        f'<td class="zentriert">0</td>'
        f'<td class="zentriert">1</td>'
        f'<td class="zentriert">{rank}:{rank - 1}</td>'
        f'<td class="zentriert">1</td>'
        f'<td class="zentriert">{rank}</td>'
        f'</tr>'
    )


class TestParseTabelle:
    def test_parses_valid_table(self):
        html = _standing_table_html(_standing_row_html(1, 'Flamengo', '281'))
        result = StandingParser.parse_tabelle(html)

        assert '281' in result
        assert result['281'] == 1

    def test_skips_invalid_rank(self):
        row_html = (
            '<tr><td>abc</td><td class="no-border-links"><a href="/verein/281/">Team</a></td></tr>'
        )
        html = _standing_table_html(row_html)
        result = StandingParser.parse_tabelle(html)

        assert result == {}

    def test_returns_empty_when_no_table(self):
        result = StandingParser.parse_tabelle('<p>No table</p>')
        assert result == {}

    def test_parse_rank_returns_int(self):
        from bs4 import BeautifulSoup

        html = '<td>5</td>'
        soup = BeautifulSoup(html, 'html.parser')
        td = soup.find('td')

        assert StandingParser._parse_rank(td) == 5

    def test_parse_rank_returns_none_on_invalid(self):
        from bs4 import BeautifulSoup

        html = '<td>abc</td>'
        soup = BeautifulSoup(html, 'html.parser')
        td = soup.find('td')

        assert StandingParser._parse_rank(td) is None


class TestParseFullTabelle:
    def test_parses_standing_row(self):
        html = _standing_table_html(_standing_row_html(1, 'Flamengo', '281'))
        result = StandingParser.parse_full_tabelle(html)

        assert len(result) == 1
        assert result[0].team == 'Flamengo'
        assert result[0].rank == 1

    def test_returns_empty_when_no_table(self):
        result = StandingParser.parse_full_tabelle('<p>No data</p>')
        assert result == []


class TestExtractCenteredCells:
    def test_extracts_cells_excluding_no_border_rechts(self):
        from bs4 import BeautifulSoup

        html = (
            '<tr>'
            '<td class="zentriert">38</td>'
            '<td class="zentriert no-border-rechts">21</td>'
            '<td class="zentriert">10</td>'
            '</tr>'
        )
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        cells = StandingParser._extract_centered_cells(row)

        assert '38' in cells
        assert '10' in cells
