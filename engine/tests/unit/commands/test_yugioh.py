import pytest

from bot.domain.commands.yugioh import YugiohCommand
from bot.domain.models.message import ImageBufferContent, ImageContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return YugiohCommand()


MOCK_CARD_DATA = {
    'data': [
        {
            'name': 'Dark Magician',
            'desc': 'The ultimate wizard\nin terms of attack\nand defense.',
            'card_images': [
                {'image_url': 'https://images.ygoprodeck.com/images/cards/46986414.jpg'}
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
    async def test_returns_card_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo')
        resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=resp)
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://images.ygoprodeck.com/images/cards/46986414.jpg'

    @pytest.mark.anyio
    async def test_strips_newlines_from_description(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo')
        resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=resp)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'The ultimate wizardin terms of attackand defense.' in caption

    @pytest.mark.anyio
    async def test_caption_contains_card_name(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo')
        resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=resp)
        messages = await command.run(data)

        assert '*Dark Magician*' in messages[0].content.caption

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo')
        resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=resp)
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo show')
        resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=resp)
        messages = await command.run(data)

        assert messages[0].content.view_once is False


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        api_resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=api_resp)
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_booster_caption_has_numbered_cards(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        api_resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=api_resp)
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
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
    async def test_booster_view_once_true_by_default(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster')
        api_resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=api_resp)
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_booster_show_flag_disables_view_once(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ygo booster show')
        api_resp = make_json_response(MOCK_CARD_DATA)

        mocker.patch('bot.domain.commands.yugioh.HttpClient.get', return_value=api_resp)
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is False
