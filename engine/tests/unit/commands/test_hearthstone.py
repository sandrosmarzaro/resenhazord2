from unittest.mock import patch

import pytest

from bot.domain.commands.hearthstone import HearthstoneCommand
from bot.domain.models.message import ImageBufferContent, ImageContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    HearthstoneCommand._cached_token = None
    return HearthstoneCommand(bnet_id='test-id', bnet_secret='test-secret')  # noqa: S106


MOCK_CARD = {
    'name': 'Fireball',
    'text': 'Deal <b>6</b> damage to a minion.',
    'flavorText': 'This spell is useful for dealing with pesky minions.',
    'image': 'https://d15f34w2p8l1cc.cloudfront.net/hearthstone/fireball.png',
}


def _mock_oauth_response():
    return make_json_response({'access_token': 'mock-token'})


def _mock_page_count_response(page_count: int = 10):
    return make_json_response({'pageCount': page_count, 'cards': []})


def _mock_card_response(card: dict | None = None):
    return make_json_response({'cards': [card or MOCK_CARD]})


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', hs', True),
            (',hs', True),
            (', HS', True),
            (', hs show', True),
            (', hs dm', True),
            (', hs booster', True),
            ('  , hs  ', True),
            ('hs', False),
            ('hello', False),
            (', hs extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSingleCard:
    @pytest.mark.anyio
    async def test_returns_card_image(self, command):
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response()],
            ),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == MOCK_CARD['image']

    @pytest.mark.anyio
    async def test_replaces_html_tags_in_caption(self, command):
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response()],
            ),
        ):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Fireball*' in caption
        assert '*6*' in caption
        assert '<b>' not in caption
        assert '</b>' not in caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command):
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response()],
            ),
        ):
            messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command):
        data = GroupCommandDataFactory.build(text=', hs show')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response()],
            ),
        ):
            messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_returns_error_when_oauth_fails(self, command):
        data = GroupCommandDataFactory.build(text=', hs')

        with patch(
            'bot.domain.commands.hearthstone.HttpClient.post',
            side_effect=Exception('OAuth Error'),
        ):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, TextContent)
        assert 'Battle.net' in messages[0].content.text


class TestCaptionEdgeCases:
    @pytest.mark.anyio
    async def test_handles_text_as_dict(self, command):
        card = {**MOCK_CARD, 'text': {'pt_BR': 'Causa <b>6</b> de dano.', 'en_US': 'Deal 6.'}}
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response(card)],
            ),
        ):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Causa *6* de dano.' in caption
        assert '<b>' not in caption

    @pytest.mark.anyio
    async def test_handles_missing_text(self, command):
        card = {k: v for k, v in MOCK_CARD.items() if k != 'text'}
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response(card)],
            ),
        ):
            messages = await command.run(data)

        assert isinstance(messages[0].content, ImageContent)

    @pytest.mark.anyio
    async def test_handles_missing_flavor_text(self, command):
        card = {k: v for k, v in MOCK_CARD.items() if k != 'flavorText'}
        data = GroupCommandDataFactory.build(text=', hs')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[_mock_page_count_response(), _mock_card_response(card)],
            ),
        ):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*Fireball*' in caption
        assert '""' not in caption


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_grid_image(self, command):
        data = GroupCommandDataFactory.build(text=', hs booster')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[
                    _mock_page_count_response(),
                    *[_mock_card_response() for _ in range(6)],
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
        data = GroupCommandDataFactory.build(text=', hs booster')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                return_value=_mock_oauth_response(),
            ),
            patch(
                'bot.domain.commands.hearthstone.HttpClient.get',
                side_effect=[
                    _mock_page_count_response(),
                    *[_mock_card_response() for _ in range(6)],
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
        assert 'Fireball' in caption

    @pytest.mark.anyio
    async def test_booster_raises_when_oauth_fails(self, command):
        data = GroupCommandDataFactory.build(text=', hs booster')

        with (
            patch(
                'bot.domain.commands.hearthstone.HttpClient.post',
                side_effect=Exception('OAuth Error'),
            ),
            pytest.raises(ValueError, match='OAuth token unavailable'),
        ):
            await command.run(data)
