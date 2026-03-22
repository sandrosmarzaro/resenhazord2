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


def _mock_translate(respx_mock, translated='Instruções traduzidas.'):
    respx_mock.get(url__startswith=TRANSLATE_URL).mock(
        return_value=httpx.Response(200, json=[[[translated, 'original']]])
    )


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
    async def test_returns_image_with_translated_recipe(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock, 'Cozinhe a massa. Adicione o molho.')
        messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/meal.jpg'
        caption = messages[0].content.caption
        assert caption is not None
        assert 'Spaghetti Bolognese' in caption
        assert 'Italian' in caption
        assert 'Spaghetti' in caption
        assert '200g' in caption
        assert 'Cozinhe a massa' in caption

    @pytest.mark.anyio
    async def test_includes_ingredients_list(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert '- Spaghetti | 200g' in caption
        assert '- Tomato | 3' in caption

    @pytest.mark.anyio
    async def test_stops_at_empty_ingredient(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        respx_mock.get(MEAL_API_URL).mock(
            return_value=httpx.Response(200, json={'meals': [_mock_meal()]})
        )
        _mock_translate(respx_mock)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        # Should only have 2 ingredients (strIngredient3 is empty)
        assert caption.count('- ') == 2

    @pytest.mark.anyio
    async def test_handles_missing_optional_fields(self, command, respx_mock):
        data = GroupCommandDataFactory.build(text=', comida')
        meal = _mock_meal(strArea=None, strTags=None, strYoutube=None, strSource=None)
        respx_mock.get(MEAL_API_URL).mock(return_value=httpx.Response(200, json={'meals': [meal]}))
        _mock_translate(respx_mock)
        messages = await command.run(data)

        caption = messages[0].content.caption
        assert caption is not None
        assert 'Sem País' in caption
