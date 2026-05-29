import httpx
import pytest

from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory

MEAL_API_URL = 'https://www.themealdb.com/api/json/v1/1/random.php'
TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'


@pytest.fixture
def command():
    return MealRecipesCommand()


def _mock_meal(**overrides):
    return {
        'strMeal': 'Spaghetti Bolognese',
        'strArea': 'Italian',
        'strCategory': 'Pasta',
        'strTags': 'Comfort,Dinner',
        'strInstructions': 'Cook the pasta. Add sauce.',
        'strMealThumb': 'https://example.com/meal.jpg',
        'strYoutube': 'https://youtube.com/watch?v=abc',
        'strSource': 'https://example.com/recipe',
        'strIngredient1': 'Spaghetti',
        'strMeasure1': '200g',
        'strIngredient2': 'Tomato',
        'strMeasure2': '3',
        'strIngredient3': '',
        'strMeasure3': '',
        **overrides,
    }


TRANSLATED_CAPTION = (
    '*Espaguete à Bolonhesa*\n'
    '\n'
    '🗺️ Italiana   🍽️ Massa   🏷️ Comfort,Dinner\n'
    '\n'
    '🍲 Ingredientes:\n'
    '- Espaguete | 200g\n'
    '- Tomate | 3\n'
    '\n'
    '📝 Passo a passo:\n'
    'Cozinhe a massa. Adicione o molho.\n'
    '🎥 https://youtube.com/watch?v=abc\n'
    '🔗 https://example.com/recipe'
)


def _mock_translate(respx_mock, translated=TRANSLATED_CAPTION):
    respx_mock.get(url__startswith=TRANSLATE_URL).mock(
        return_value=httpx.Response(200, json=[[[translated, '']]])
    )


class TestMatches:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            (', comida', True),
            (',comida', True),
            (', COMIDA', True),
            (', comida show', True),
            (', comida dm', True),
            ('  , comida  ', True),
            ('comida', False),
            ('hello', False),
            (', comida extra', False),
        ],
    )
    def test_matches(self, command, text, expected):
        assert command.matches(text) is expected


class TestRun:
    @pytest.mark.anyio
    async def test_calls_api(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        route = respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock)
        await command.run(data)

        assert route.called

    @pytest.mark.anyio
    async def test_makes_only_one_translate_call(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        translate_route = respx_mock.get(url__startswith=TRANSLATE_URL).mock(
            return_value=httpx.Response(200, json=[[[TRANSLATED_CAPTION, '']]])
        )
        await command.run(data)

        assert translate_route.call_count == 1

    @pytest.mark.anyio
    async def test_returns_image_with_translated_recipe(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/meal.jpg'
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Espaguete à Bolonhesa' in caption
        assert 'Italiana' in caption
        assert 'Espaguete' in caption
        assert '200g' in caption
        assert 'Cozinhe a massa' in caption

    @pytest.mark.anyio
    async def test_translate_receives_full_english_caption(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        translate_route = respx_mock.get(url__startswith=TRANSLATE_URL).mock(
            return_value=httpx.Response(200, json=[[[TRANSLATED_CAPTION, '']]])
        )
        await command.run(data)

        q = translate_route.calls[0].request.url.params['q']
        assert 'Spaghetti' in q
        assert 'Tomato' in q
        assert 'Italian' in q
        assert 'Cook the pasta' in q

    @pytest.mark.anyio
    async def test_includes_ingredients_in_translation_input(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert '- Espaguete | 200g' in caption
        assert '- Tomate | 3' in caption

    @pytest.mark.anyio
    async def test_stops_at_empty_ingredient(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        translate_route = respx_mock.get(url__startswith=TRANSLATE_URL).mock(
            return_value=httpx.Response(200, json=[[[TRANSLATED_CAPTION, '']]])
        )
        await command.run(data)

        # English caption sent to translator should only have 2 ingredients
        q = translate_route.calls[0].request.url.params['q']
        assert q.count('- ') == 2

    @pytest.mark.anyio
    async def test_handles_missing_optional_fields(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        meal = _mock_meal(strArea=None, strTags=None, strYoutube=None, strSource=None)
        respx_mock.get(MEAL_API_URL).mock(return_value=httpx.Response(200, json={'meals': [meal]}))
        translated = (
            '*Espaguete à Bolonhesa*\n'
            '\n'
            '🗺️ Desconhecido   🍽️ Massa\n'
            '\n'
            '🍲 Ingredientes:\n'
            '- Espaguete | 200g\n'
            '- Tomate | 3\n'
            '\n'
            '📝 Passo a passo:\n'
            'Cozinhe a massa. Adicione o molho.'
        )
        _mock_translate(respx_mock, translated=translated)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Desconhecido' in caption
