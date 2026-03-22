import httpx
import pytest

from bot.domain.commands.rule34 import Rule34Command
from bot.domain.exceptions import ExternalServiceError
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return Rule34Command()


SAMPLE_HTML = """
<div class="flexi">
    <img src="https://example.com/image1.jpg" />
    <img src="https://example.com/image2.jpg" />
</div>
"""

BANNER_FIRST_HTML = """
<div class="flexi">
    <img src="https://kanako.store/products/futa-body" />
    <img src="https://example.com/real-image.jpg" />
</div>
"""

NO_IMAGES_HTML = """
<div class="flexi">
</div>
"""


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', rule 34', True),
            (',rule 34', True),
            (', RULE 34', True),
            (', rule 34 show', True),
            (', rule 34 dm', True),
            ('  , rule 34  ', True),
            ('rule 34', False),
            ('hello', False),
            (', rule 34 extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_returns_image(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', rule 34')
        respx_mock.get(url__startswith='https://rule34.xxx/').mock(
            return_value=httpx.Response(200, text=SAMPLE_HTML)
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/image1.jpg'
        assert messages[0].content.caption == 'Aqui está a imagem que você pediu 🤗'

    @pytest.mark.anyio
    async def test_skips_banner_url(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', rule 34')
        respx_mock.get(url__startswith='https://rule34.xxx/').mock(
            return_value=httpx.Response(200, text=BANNER_FIRST_HTML)
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/real-image.jpg'

    @pytest.mark.anyio
    async def test_raises_when_no_images(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', rule 34')
        respx_mock.get(url__startswith='https://rule34.xxx/').mock(
            return_value=httpx.Response(200, text=NO_IMAGES_HTML)
        )
        with pytest.raises(ExternalServiceError, match='Nenhuma imagem encontrada'):
            await command.run(data)

    @pytest.mark.anyio
    async def test_view_once_is_true(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', rule 34')
        respx_mock.get(url__startswith='https://rule34.xxx/').mock(
            return_value=httpx.Response(200, text=SAMPLE_HTML)
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is True
