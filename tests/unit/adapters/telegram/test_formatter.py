from bot.adapters.telegram.formatter import whatsapp_to_html


class TestPlainText:
    def test_empty_string_returns_empty(self):
        assert whatsapp_to_html('') == ''

    def test_plain_text_unchanged(self):
        assert whatsapp_to_html('hello world') == 'hello world'


class TestEscaping:
    def test_less_than_escaped(self):
        assert whatsapp_to_html('1 < 2') == '1 &lt; 2'

    def test_ampersand_escaped(self):
        assert whatsapp_to_html('a & b') == 'a &amp; b'

    def test_greater_than_escaped_when_not_blockquote(self):
        assert whatsapp_to_html('a>b') == 'a&gt;b'


class TestBold:
    def test_basic_bold(self):
        assert whatsapp_to_html('oi *mundo*') == 'oi <b>mundo</b>'

    def test_multiple_bold_segments(self):
        assert whatsapp_to_html('*um* e *dois*') == '<b>um</b> e <b>dois</b>'

    def test_bold_across_words(self):
        assert whatsapp_to_html('*hello world*') == '<b>hello world</b>'


class TestItalic:
    def test_basic_italic(self):
        assert whatsapp_to_html('_ola_') == '<i>ola</i>'

    def test_snake_case_preserved(self):
        assert whatsapp_to_html('foo_bar_baz') == 'foo_bar_baz'

    def test_italic_after_space(self):
        assert whatsapp_to_html('diga _oi_ amigo') == 'diga <i>oi</i> amigo'


class TestBlockquote:
    def test_single_line(self):
        assert whatsapp_to_html('> texto') == '<blockquote>texto</blockquote>'

    def test_consecutive_lines_merge(self):
        assert whatsapp_to_html('> um\n> dois') == '<blockquote>um\ndois</blockquote>'

    def test_blockquote_mixed_with_plain(self):
        assert (
            whatsapp_to_html('antes\n> quote\ndepois')
            == 'antes\n<blockquote>quote</blockquote>\ndepois'
        )

    def test_non_prefix_greater_than_is_escaped(self):
        assert whatsapp_to_html('a > b') == 'a &gt; b'


class TestCombined:
    def test_bold_inside_blockquote(self):
        assert (
            whatsapp_to_html('> *titulo*\ntexto') == '<blockquote><b>titulo</b></blockquote>\ntexto'
        )

    def test_bold_and_italic_together(self):
        assert whatsapp_to_html('*forte* _fraco_') == '<b>forte</b> <i>fraco</i>'
