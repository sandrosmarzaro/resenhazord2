from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.magic_the_gathering import MagicTheGatheringCommand
from bot.domain.models.message import ImageBufferContent, ImageContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return MagicTheGatheringCommand()


MOCK_CARD = {
    'name': 'Lightning Bolt',
    'text': 'Lightning Bolt deals 3 damage to any target.',
    'imageUrl': 'https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=234704',
}


def _mock_total_count_response(total: int = 500):
    mock = MagicMock()
    mock.headers = {'total-count': str(total)}
    mock.raise_for_status.return_value = None
    mock.json.return_value = {'cards': []}
    return mock


def _mock_cards_response(cards: list | None = None):
    return make_json_response({'cards': cards or [MOCK_CARD]})


def _mock_head_response(url: str | None = None):
    mock = MagicMock()
    mock.url = url or MOCK_CARD['imageUrl']
    mock.raise_for_status.return_value = None
    return mock


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
    async def test_returns_card_image(self, command):
        data = GroupCommandDataFactory.build(text=', mtg')

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(500),
                _mock_cards_response(),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == MOCK_CARD['imageUrl']

    @pytest.mark.anyio
    async def test_caption_contains_card_info(self, command):
        data = GroupCommandDataFactory.build(text=', mtg')

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(),
                _mock_cards_response(),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Lightning Bolt*' in caption
        assert 'Lightning Bolt deals 3 damage' in caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command):
        data = GroupCommandDataFactory.build(text=', mtg')

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(),
                _mock_cards_response(),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command):
        data = GroupCommandDataFactory.build(text=', mtg show')

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(),
                _mock_cards_response(),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_skips_cards_with_multiverseid_zero(self, command):
        data = GroupCommandDataFactory.build(text=', mtg')
        bad_card = {
            'name': 'Bad Card',
            'text': 'text',
            'imageUrl': 'https://example.com/Image.ashx?multiverseid=0',
        }

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(100),
                _mock_cards_response([bad_card, MOCK_CARD]),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        assert messages[0].content.url == MOCK_CARD['imageUrl']

    @pytest.mark.anyio
    async def test_skips_card_back_redirect(self, command):
        data = GroupCommandDataFactory.build(text=', mtg')

        with patch(
            'bot.domain.commands.magic_the_gathering.HttpClient.get',
            side_effect=[
                _mock_total_count_response(100),
                _mock_cards_response(),
                _mock_head_response('https://gatherer.wizards.com/assets/card_back.webp'),
                _mock_cards_response(),
                _mock_head_response(),
            ],
        ):
            messages = await command.run(data)

        assert messages[0].content.url == MOCK_CARD['imageUrl']


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_grid_image(self, command):
        data = GroupCommandDataFactory.build(text=', mtg booster')

        with (
            patch(
                'bot.domain.commands.magic_the_gathering.HttpClient.get',
                side_effect=[
                    _mock_total_count_response(600),
                    *[
                        resp
                        for _ in range(6)
                        for resp in (
                            _mock_cards_response(),
                            _mock_head_response(),
                        )
                    ],
                ],
            ),
            patch(
                'bot.domain.commands.card_booster.HttpClient.get_buffer',
                return_value=b'fake-image',
            ),
            patch(
                'bot.domain.commands.card_booster.build_card_grid',
                return_value=b'grid-image',
            ),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_booster_caption_has_numbered_cards(self, command):
        data = GroupCommandDataFactory.build(text=', mtg booster')

        with (
            patch(
                'bot.domain.commands.magic_the_gathering.HttpClient.get',
                side_effect=[
                    _mock_total_count_response(600),
                    *[
                        resp
                        for _ in range(6)
                        for resp in (
                            _mock_cards_response(),
                            _mock_head_response(),
                        )
                    ],
                ],
            ),
            patch(
                'bot.domain.commands.card_booster.HttpClient.get_buffer',
                return_value=b'fake-image',
            ),
            patch(
                'bot.domain.commands.card_booster.build_card_grid',
                return_value=b'grid-image',
            ),
        ):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*1.*' in caption
        assert 'Lightning Bolt' in caption
