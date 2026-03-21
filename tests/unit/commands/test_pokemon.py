import httpx
import pytest

from bot.domain.commands.pokemon import PokemonCommand
from bot.domain.models.message import ImageBufferContent
from tests.factories.command_data import GroupCommandDataFactory

MOCK_POKEMON = {
    'name': 'pikachu',
    'id': 25,
    'types': [{'type': {'name': 'electric'}}],
    'sprites': {
        'front_default': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png',
        'other': {
            'official-artwork': {
                'front_default': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png',
            },
        },
    },
}

MOCK_POKEMON_NO_ARTWORK = {
    **MOCK_POKEMON,
    'name': 'missingno',
    'sprites': {
        'front_default': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png',
        'other': {'official-artwork': {'front_default': None}},
    },
}


@pytest.fixture
def command():
    return PokemonCommand()


@pytest.fixture
def pokemon_route(respx_mock):
    return respx_mock.get(url__startswith='https://pokeapi.co/api/v2/pokemon/')


@pytest.fixture
def image_route(respx_mock):
    return respx_mock.get(url__startswith='https://raw.githubusercontent.com/').mock(
        return_value=httpx.Response(200, content=b'fake-pokemon-image')
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', pokémon', True),
            (',pokémon', True),
            (', pokemon', True),
            (', POKÉMON', True),
            (', pokémon team', True),
            (', pokémon show', True),
            (', pokémon dm', True),
            ('  , pokémon  ', True),
            ('pokémon', False),
            ('hello', False),
            (', pokémon extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestSinglePokemon:
    @pytest.mark.anyio
    async def test_returns_image_buffer(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_downloads_official_artwork(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        await command.run(data)

        request = image_route.calls.last.request
        assert 'official-artwork' in str(request.url)

    @pytest.mark.anyio
    async def test_caption_contains_name_type_dex(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Pikachu' in caption
        assert '⚡' in caption
        assert '#25' in caption

    @pytest.mark.anyio
    async def test_fallback_to_front_default_when_no_artwork(
        self, command, pokemon_route, image_route
    ):
        data = GroupCommandDataFactory.build(text=',pokémon')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON_NO_ARTWORK))
        await command.run(data)

        request = image_route.calls.last.request
        assert str(request.url) == MOCK_POKEMON_NO_ARTWORK['sprites']['front_default']

    @pytest.mark.anyio
    async def test_view_once_true_by_default(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        messages = await command.run(data)

        assert messages[0].content.view_once is True

    @pytest.mark.anyio
    async def test_show_flag_disables_view_once(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon show')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        messages = await command.run(data)

        assert messages[0].content.view_once is False

    @pytest.mark.anyio
    async def test_dm_flag_redirects_jid(self, command, pokemon_route, image_route):
        data = GroupCommandDataFactory.build(text=',pokémon dm')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        messages = await command.run(data)

        assert messages[0].jid == data.participant


class TestTeamMode:
    @pytest.mark.anyio
    async def test_returns_grid_image(self, command, pokemon_route, mocker):
        data = GroupCommandDataFactory.build(text=',pokémon team')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageBufferContent)

    @pytest.mark.anyio
    async def test_fetches_6_pokemon(self, command, pokemon_route, mocker):
        data = GroupCommandDataFactory.build(text=',pokémon team')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        await command.run(data)

        assert pokemon_route.call_count == 6

    @pytest.mark.anyio
    async def test_caption_has_numbered_labels(self, command, pokemon_route, mocker):
        data = GroupCommandDataFactory.build(text=',pokémon team')
        pokemon_route.mock(return_value=httpx.Response(200, json=MOCK_POKEMON))
        mocker.patch(
            'bot.domain.commands.card_booster.build_card_grid',
            return_value=b'grid-image',
        )
        mocker.patch(
            'bot.domain.commands.card_booster.HttpClient.get_buffer',
            return_value=b'fake-image',
        )
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert '*1.*' in caption
        assert 'Pikachu' in caption
        assert '⚡' in caption
