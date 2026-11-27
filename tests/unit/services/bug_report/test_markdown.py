from bot.domain.services.bug_report.markdown import Markdown


class TestCode:
    def test_wraps_a_value_in_a_code_span(self):
        assert Markdown.code(',moeda iene') == '`,moeda iene`'

    def test_a_backtick_cannot_close_the_span(self):
        assert Markdown.code('a`b') == "`a'b`"

    def test_a_pipe_cannot_split_a_table_cell(self):
        assert Markdown.code('a|b') == '`a\\|b`'

    def test_a_newline_stays_in_the_cell(self):
        assert Markdown.code('a\nb') == '`a b`'


class TestText:
    def test_a_mention_pings_nobody(self):
        assert Markdown.text('valeu @sandro') == 'valeu @\u200bsandro'

    def test_a_pipe_cannot_split_a_table_cell(self):
        assert Markdown.text('a|b') == 'a\\|b'


class TestQuote:
    def test_quotes_every_line(self):
        assert Markdown.quote('a\nb') == '> a\n> b'

    def test_quoted_text_pings_nobody(self):
        assert Markdown.quote('@sandro') == '> @\u200bsandro'
