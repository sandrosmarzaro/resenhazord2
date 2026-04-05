from typing import ClassVar

import httpx
import pytest

from bot.domain.commands.pokemon_tcg import PokemonTCGCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory


@pytest.fixture
def command():
    return PokemonTCGCommand()


@pytest.fixture
def card_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.tcgdex.net/v2/en/random/card')


@pytest.fixture
def image_route(respx_mock):
    return respx_mock.get(url__startswith='https://assets.tcgdex.net/').mock(
        return_value=httpx.Response(200, content=b'fake-image')
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', pokemontcg', True),
            (',pokemontcg', True),
            (', POKEMONTCG', True),
            (', pokémontcg', True),
            (', pokemontcg show', True),
            (', pokemontcg dm', True),
            (', pokemontcg booster', True),
            (',ptcg', True),
            (', ptcg', True),
            (', ptcg show', True),
            (', ptcg booster', True),
            ('pokemontcg', False),
            ('hello', False),
            (', pokemontcg extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSingleCard:
    MOCK_CARD: ClassVar[dict] = {
        'id': 'base1-4',
        'localId': '4',
        'name': 'Charizard',
        'category': 'Pokemon',
        'image': 'https://assets.tcgdex.net/en/base/base1/4',
        'illustrator': 'Mitsuhiro Arita',
        'rarity': 'Rare',
        'hp': 120,
        'types': ['Fire'],
        'stage': 'Stage2',
        'set': {
            'name': 'Base Set',
            'cardCount': {'total': 102, 'official': 102},
        },
    }

    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_downloads_webp_image(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        await command.run(data)

        url = str(image_route.calls.last.request.url)
        assert url.endswith('/high.webp')

    @pytest.mark.anyio
    async def test_caption_contains_card_metadata(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Charizard*' in caption
        assert 'Pokemon' in caption
        assert 'Stage2' in caption
        assert 'HP: 120' in caption
        assert '🔥' in caption
        assert 'Base Set' in caption
        assert '#4/102' in caption
        assert 'Rare' in caption
        assert 'Mitsuhiro Arita' in caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg show')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_retries_when_no_image(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        no_image_card = {**self.MOCK_CARD, 'image': None}
        card_route.mock(
            side_effect=[
                httpx.Response(200, json=no_image_card),
                httpx.Response(200, json=self.MOCK_CARD),
            ]
        )
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_when_all_retries_fail(self, command, card_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        no_image_card = {**self.MOCK_CARD, 'image': None}
        card_route.mock(return_value=httpx.Response(200, json=no_image_card))
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'encontrar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_returns_error_on_exception(self, command, card_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        card_route.mock(side_effect=Exception('timeout'))
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'buscar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_handles_card_without_optional_fields(self, command, card_route, image_route):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        minimal_card = {
            'id': 'base1-99',
            'localId': '99',
            'name': 'Energy',
            'category': 'Energy',
            'image': 'https://assets.tcgdex.net/en/base/base1/99',
            'set': {
                'name': 'Base Set',
                'cardCount': {'total': 102, 'official': 102},
            },
        }
        card_route.mock(return_value=httpx.Response(200, json=minimal_card))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)


class TestBooster:
    MOCK_CARD: ClassVar[dict] = {
        'id': 'base1-4',
        'localId': '4',
        'name': 'Charizard',
        'category': 'Pokemon',
        'image': 'https://assets.tcgdex.net/en/base/base1/4',
        'illustrator': 'Mitsuhiro Arita',
        'rarity': 'Rare',
        'hp': 120,
        'types': ['Fire'],
        'stage': 'Stage2',
        'set': {
            'name': 'Base Set',
            'cardCount': {'total': 102, 'official': 102},
        },
    }

    @pytest.mark.anyio
    async def test_returns_grid_image(self, command, card_route, image_route, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_booster_label_contains_metadata(self, command, card_route, image_route, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Pokemon Stage2' in caption
        assert '🔥' in caption
        assert 'HP: 120' in caption
        assert '⭐ Rare' in caption

    @pytest.mark.anyio
    async def test_booster_downloads_webp(self, command, card_route, image_route, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')
        card_route.mock(return_value=httpx.Response(200, json=self.MOCK_CARD))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        await command.run(data)

        url = str(image_route.calls.last.request.url)
        assert url.endswith('/high.webp')
