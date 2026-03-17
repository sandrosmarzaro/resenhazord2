import httpx
import pytest

from bot.domain.commands.bicho import BichoCommand
from bot.domain.models.message import TextContent
from tests.factories.command_data import GroupCommandDataFactory

BICHO_URL = 'https://www.eojogodobicho.com/deu-no-poste.html'

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


@pytest.fixture
def command():
    return BichoCommand()


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
    @pytest.mark.anyio
    async def test_returns_latest_published_draw(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(BICHO_URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
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
        respx_mock.get(BICHO_URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'PTN 18h' in text

    @pytest.mark.anyio
    async def test_unpublished_draw_returns_pending_message(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho cor')
        respx_mock.get(BICHO_URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        messages = await command.run(data)

        text = messages[0].content.text
        assert 'ainda não foi publicado' in text

    @pytest.mark.anyio
    async def test_no_published_draws(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        html = '<div id="bloco-PPT"><span class="status-pendente"></span></div>'
        respx_mock.get(BICHO_URL).mock(return_value=httpx.Response(200, text=html))
        messages = await command.run(data)

        assert 'Nenhum sorteio publicado' in messages[0].content.text

    @pytest.mark.anyio
    async def test_error_returns_error_message(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', bicho')
        respx_mock.get(BICHO_URL).mock(side_effect=Exception('Network error'))
        messages = await command.run(data)

        assert 'Erro' in messages[0].content.text
