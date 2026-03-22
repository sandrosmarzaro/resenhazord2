import httpx
import pytest

from bot.domain.commands.magic_the_gathering import MagicTheGatheringCommand
from bot.domain.models.message import ImageBufferContent, ImageContent
from tests.factories.command_data import GroupCommandDataFactory

MOCK_CARD = {
    'name': 'Lightning Bolt',
    'type': 'Instant',
    'rarity': 'Common',
    'manaCost': '{R}',
    'text': 'Lightning Bolt deals 3 damage to any target.',
    'imageUrl': 'https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=234704',
}

MOCK_CREATURE = {
    'name': 'Tarmogoyf',
    'type': 'Creature — Lhurgoyf',
    'rarity': 'Mythic Rare',
    'manaCost': '{1}{G}',
    'text': "Tarmogoyf's power is equal to the number of card types among cards in all graveyards.",
    'power': '*',
    'toughness': '1+*',
    'imageUrl': 'https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=370404',
}


@pytest.fixture
def command():
    return MagicTheGatheringCommand()


@pytest.fixture
def cards_route(respx_mock):
    return respx_mock.get(url__startswith='https://api.magicthegathering.io/v1/cards')


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', mtg', True),
            (',mtg', True),
            (', MTG', True),
            (', mtg show', True),
            (', mtg dm', True),
            (', mtg booster', True),
            ('  , mtg  ', True),
            ('mtg', False),
            ('hello', False),
            (', mtg extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSingleCard:
    @pytest.mark.anyio
    async def test_returns_card_image(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '500'}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == MOCK_CARD['imageUrl']

    @pytest.mark.anyio
    async def test_caption_contains_name_type_and_rarity(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '500'}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Lightning Bolt* — Instant' in caption
        assert '💎 Common' in caption
        assert '{R}' in caption
        assert 'Lightning Bolt deals 3 damage' in caption

    @pytest.mark.anyio
    async def test_creature_shows_power_toughness(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '500'}),
                httpx.Response(200, json={'cards': [MOCK_CREATURE]}),
            ]
        )
        respx_mock.get(MOCK_CREATURE['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '⚔️ */1+*' in caption
        assert '💎 Mythic Rare' in caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '500'}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg show')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '500'}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_skips_cards_with_multiverseid_zero(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        bad_card = {
            'name': 'Bad Card',
            'text': 'text',
            'imageUrl': 'https://example.com/Image.ashx?multiverseid=0',
        }
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '100'}),
                httpx.Response(200, json={'cards': [bad_card, MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        assert messages[0].content.url == MOCK_CARD['imageUrl']

    @pytest.mark.anyio
    async def test_skips_card_back_redirect(self, command, cards_route, respx_mock):
        data = GroupCommandDataFactory.build(text=', mtg')
        card_back_url = 'https://gatherer.wizards.com/assets/card_back.webp'
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '100'}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
                httpx.Response(200, json={'cards': [MOCK_CARD]}),
            ]
        )
        respx_mock.get(MOCK_CARD['imageUrl']).mock(
            side_effect=[
                httpx.Response(302, headers={'location': card_back_url}),
                httpx.Response(200),
            ]
        )
        respx_mock.get(card_back_url).mock(return_value=httpx.Response(200))
        messages = await command.run(data)

        assert messages[0].content.url == MOCK_CARD['imageUrl']


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_grid_image(self, command, cards_route, respx_mock, mocker):
        data = GroupCommandDataFactory.build(text=', mtg booster')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '600'}),
                *[
                    resp
                    for _ in range(6)
                    for resp in (httpx.Response(200, json={'cards': [MOCK_CARD]}),)
                ],
            ]
        )
        respx_mock.get(url__startswith='https://gatherer.wizards.com/').mock(
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
    async def test_booster_caption_has_numbered_cards(
        self, command, cards_route, respx_mock, mocker
    ):
        data = GroupCommandDataFactory.build(text=', mtg booster')
        cards_route.mock(
            side_effect=[
                httpx.Response(200, json={'cards': []}, headers={'total-count': '600'}),
                *[
                    resp
                    for _ in range(6)
                    for resp in (httpx.Response(200, json={'cards': [MOCK_CARD]}),)
                ],
            ]
        )
        respx_mock.get(url__startswith='https://gatherer.wizards.com/').mock(
            return_value=httpx.Response(200, content=b'fake-image')
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*1.*' in caption
        assert 'Lightning Bolt' in caption
