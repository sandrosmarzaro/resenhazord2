import httpx
import pytest

from bot.domain.commands.yugioh import YugiohCommand
from bot.domain.models.message import ImageBufferContent, ImageContent
from tests.factories.command_data import GroupCommandDataFactory

YGO_API_URL = 'https://db.ygoprodeck.com/api/v7/randomcard.php'

MOCK_CARD_DATA = {
    'data': [
        {
            'name': 'Dark Magician',
            'type': 'Normal Monster',
            'humanReadableCardType': 'Normal Monster',
            'desc': 'The ultimate wizard\nin terms of attack\nand defense.',
            'atk': 2500,
            'def': 2100,
            'level': 7,
            'race': 'Spellcaster',
            'attribute': 'DARK',
            'card_images': [
                {'image_url': 'https://images.ygoprodeck.com/images/cards/46986414.jpg'}
            ],
        }
    ]
}

MOCK_SPELL_DATA = {
    'data': [
        {
            'name': 'Monster Reborn',
            'type': 'Spell Card',
            'humanReadableCardType': 'Normal Spell',
            'desc': 'Target 1 monster in either GY; Special Summon it.',
            'race': 'Normal',
            'card_images': [
                {'image_url': 'https://images.ygoprodeck.com/images/cards/83764718.jpg'}
            ],
        }
    ]
}


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', ygo', True),
            (',ygo', True),
            (', YGO', True),
            (', ygo show', True),
            (', ygo dm', True),
            (', ygo booster', True),
            ('  , ygo  ', True),
            ('ygo', False),
            ('hello', False),
            (', ygo extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSingleCard:
    @pytest.mark.anyio
    async def test_returns_card_image(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://images.ygoprodeck.com/images/cards/46986414.jpg'

    @pytest.mark.anyio
    async def test_caption_contains_name_and_type(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Dark Magician* — Normal Monster' in caption

    @pytest.mark.anyio
    async def test_caption_shows_atk_def_level(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'ATK: 2500' in caption
        assert 'DEF: 2100' in caption
        assert 'Lv. 7' in caption

    @pytest.mark.anyio
    async def test_caption_shows_attribute_and_race(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '🌑 DARK' in caption
        assert 'Spellcaster' in caption

    @pytest.mark.anyio
    async def test_caption_preserves_newlines_as_quote_lines(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '> The ultimate wizard' in caption
        assert '> in terms of attack' in caption
        assert '> and defense.' in caption

    @pytest.mark.anyio
    async def test_spell_card_omits_monster_stats(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_SPELL_DATA))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Monster Reborn* — Normal Spell' in caption
        assert 'ATK' not in caption
        assert 'DEF' not in caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', ygo show')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        messages = await command.run(data)

        assert messages[0].content.view_once is False


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        respx_mock.get(url__startswith='https://images.ygoprodeck.com/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_booster_caption_has_numbered_cards(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        respx_mock.get(url__startswith='https://images.ygoprodeck.com/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*1.*' in caption
        assert 'Dark Magician' in caption

    @pytest.mark.anyio
    async def test_booster_view_once_true_by_default(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        respx_mock.get(url__startswith='https://images.ygoprodeck.com/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_booster_show_flag_disables_view_once(self, command, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster show')
        respx_mock.get(YGO_API_URL).mock(return_value=httpx.Response(200, json=MOCK_CARD_DATA))
        respx_mock.get(url__startswith='https://images.ygoprodeck.com/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is False


@pytest.fixture
def command():
    return YugiohCommand()
