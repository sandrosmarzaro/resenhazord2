import re

import httpx
import pytest

from bot.domain.commands.lottery import LotteryCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return LotteryCommand()


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', bicho', True),
            (',bicho', True),
            (', BICHO', True),
            (', bicho ptn', True),
            (', bicho cor', True),
            ('  , bicho  ', True),
            ('bicho', False),
            ('hello', False),
            (', bicho invalid', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    URL = 'https://www.eojogodobicho.com/deu-no-poste.html'
    SAMPLE_HTML = """
<div id="bloco-PTN">
    <span class="status-publicado"></span>
    <table class="dnp-table">
        <tbody>
            <tr>
                <td>1</td>
                <td class="dnp-milhar">1234</td>
                <td><a>10</a></td>
                <td><a>Coelho</a></td>
            </tr>
            <tr>
                <td>2</td>
                <td class="dnp-milhar">5678</td>
                <td><a>5</a></td>
                <td><a>Cachorro</a></td>
            </tr>
        </tbody>
    </table>
</div>
<div id="bloco-COR">
    <span class="status-pendente"></span>
</div>
"""

    @pytest.mark.anyio
    async def test_returns_latest_published_draw(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.SAMPLE_HTML))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        text = messages[0].content.text
        assert 'PTN 18h' in text
        assert '1234' in text
        assert 'Coelho' in text

    @pytest.mark.anyio
    async def test_returns_specific_draw_by_arg(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho ptn')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.SAMPLE_HTML))
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'PTN 18h' in text

    @pytest.mark.anyio
    async def test_unpublished_draw_returns_pending_message(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho cor')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.SAMPLE_HTML))
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'ainda não foi publicado' in text

    @pytest.mark.anyio
    async def test_error_returns_error_message(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(self.URL).mock(side_effect=Exception('Network error'))
        messages = await command.run(data)

        assert 'Erro' in messages[0].content.text


class TestYesterdayFallback:
    URL = 'https://www.eojogodobicho.com/deu-no-poste.html'
    YESTERDAY_URL_PATTERN = re.compile(
        r'https://www\.eojogodobicho\.com/resultados/rio/resultados-do-bicho-\d{2}-\d{2}-\d{4}\.html'
    )
    NO_PUBLISHED_HTML = '<div id="bloco-PPT"><span class="status-pendente"></span></div>'
    YESTERDAY_HTML = """
<div id="bloco-COR">
    <span class="status-publicado"></span>
    <table class="dnp-table">
        <tbody>
            <tr>
                <td>1</td>
                <td class="dnp-milhar">9999</td>
                <td><a>3</a></td>
                <td><a>Burro</a></td>
            </tr>
        </tbody>
    </table>
</div>
"""

    @pytest.mark.anyio
    async def test_falls_back_to_yesterday_when_no_today_draws(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.NO_PUBLISHED_HTML))
        respx_mock.get(url__regex=self.YESTERDAY_URL_PATTERN).mock(
            return_value=httpx.Response(200, text=self.YESTERDAY_HTML)
        )

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'Coruja 21h' in text
        assert '(ontem)' in text
        assert '9999' in text
        assert 'Burro' in text

    @pytest.mark.anyio
    async def test_shows_no_draws_message_when_yesterday_also_empty(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.NO_PUBLISHED_HTML))
        respx_mock.get(url__regex=self.YESTERDAY_URL_PATTERN).mock(
            return_value=httpx.Response(200, text=self.NO_PUBLISHED_HTML)
        )

        messages = await command.run(data)

        assert 'Nenhum sorteio publicado' in messages[0].content.text

    @pytest.mark.anyio
    async def test_shows_no_draws_message_when_yesterday_fetch_fails(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.NO_PUBLISHED_HTML))
        respx_mock.get(url__regex=self.YESTERDAY_URL_PATTERN).mock(
            side_effect=httpx.HTTPError('Network error')
        )

        messages = await command.run(data)

        assert 'Nenhum sorteio publicado' in messages[0].content.text

    @pytest.mark.anyio
    async def test_no_fallback_when_specific_arg_given(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho ppt')
        respx_mock.get(self.URL).mock(return_value=httpx.Response(200, text=self.NO_PUBLISHED_HTML))

        messages = await command.run(data)

        text = messages[0].content.text
        assert 'ainda não foi publicado' in text
        assert respx_mock.calls.call_count == 1
