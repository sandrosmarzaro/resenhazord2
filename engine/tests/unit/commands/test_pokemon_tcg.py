import pytest

from bot.domain.commands.pokemon_tcg import PokemonTCGCommand
from bot.domain.models.message import ImageBufferContent, TextContent
from tests.factories.command_data import GroupCommandDataFactory
from tests.factories.mock_http import make_json_response


@pytest.fixture
def command():
    return PokemonTCGCommand()


MOCK_CARD = {
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


def _mock_card_response(card: dict | None = None):
    return make_json_response(card or MOCK_CARD)


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
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_downloads_webp_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mock_get_buffer = mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        await command.run(data)

        url = mock_get_buffer.call_args[0][0]
        assert url.endswith('/high.webp')

    @pytest.mark.anyio
    async def test_caption_contains_card_metadata(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
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
    async def test_view_once_true_by_default(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg show')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_retries_when_no_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        no_image_card = {**MOCK_CARD, 'image': None}
        no_image_resp = make_json_response(no_image_card)
        with_image_resp = _mock_card_response()

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            side_effect=[no_image_resp, with_image_resp],
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_returns_error_when_all_retries_fail(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')
        no_image_card = {**MOCK_CARD, 'image': None}
        no_image_resp = make_json_response(no_image_card)

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=no_image_resp,
        )
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'encontrar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_returns_error_on_exception(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', pokemontcg')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            side_effect=Exception('timeout'),
        )
        messages = await command.run(data)

        assert isinstance(messages[0].content, TextContent)
        assert 'buscar' in messages[0].content.text

    @pytest.mark.anyio
    async def test_handles_card_without_optional_fields(self, command, mocker):
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

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=make_json_response(minimal_card),
        )
        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)


class TestBooster:
    @pytest.mark.anyio
    async def test_returns_grid_image(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
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
    async def test_booster_label_contains_metadata(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
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
        assert 'Pokemon Stage2' in caption
        assert '🔥' in caption
        assert 'HP: 120' in caption
        assert '⭐ Rare' in caption

    @pytest.mark.anyio
    async def test_booster_downloads_webp(self, command, mocker):
        data = GroupCommandDataFactory.build(text=', ptcg booster')

        mocker.patch(
            'bot.domain.commands.pokemon_tcg.HttpClient.get',
            return_value=_mock_card_response(),
        )
        mock_get_buffer = mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        await command.run(data)

        url = mock_get_buffer.call_args[0][0]
        assert url.endswith('/high.webp')
