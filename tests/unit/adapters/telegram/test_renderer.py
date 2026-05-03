from bot.domain.models.contents.text_content import TextContent
from bot.domain.models.message import BotMessage
from bot.ports.telegram_port import TelegramKind
from tests.unit.adapters.telegram.conftest import CHAT_ID, render


class TestText:
    def test_single_chunk(self, renderer):
        outbounds = render(renderer, TextContent(text='hello'))

        assert len(outbounds) == 1
        assert outbounds[0].kind == TelegramKind.TEXT
        assert outbounds[0].text == 'hello'

    def test_bold_markdown_becomes_html(self, renderer):
        outbounds = render(renderer, TextContent(text='oi *mundo*'))

        assert outbounds[0].text == 'oi <b>mundo</b>'

    def test_blockquote_prefix_becomes_blockquote(self, renderer):
        outbounds = render(renderer, TextContent(text='> citacao'))

        assert outbounds[0].text == '<blockquote>citacao</blockquote>'

    def test_splits_beyond_limit(self, renderer):
        long_text = 'a' * (renderer.MAX_TEXT_LENGTH + 50)

        outbounds = render(renderer, TextContent(text=long_text))

        assert len(outbounds) == 2
        assert all(out.kind == TelegramKind.TEXT for out in outbounds)
        assert ''.join(out.text or '' for out in outbounds) == long_text


class TestRenderMany:
    def test_concatenates_outbounds(self, renderer):
        messages = [
            BotMessage(jid='jid', content=TextContent(text='one')),
            BotMessage(jid='jid', content=TextContent(text='two')),
        ]

        outbounds = renderer.render_many(messages, CHAT_ID)

        assert [out.text for out in outbounds] == ['one', 'two']
