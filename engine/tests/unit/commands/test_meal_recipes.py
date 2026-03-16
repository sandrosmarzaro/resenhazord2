from unittest.mock import MagicMock, patch

import pytest

from bot.domain.commands.meal_recipes import MealRecipesCommand
from bot.domain.models.message import ImageContent
from tests.factories.command_data import GroupCommandDataFactory


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


def _mock_response(meal):
    mock = MagicMock()
    mock.json.return_value = {'meals': [meal]}
    mock.raise_for_status.return_value = None
    return mock


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
    async def test_calls_api(self, command):
        data = GroupCommandDataFactory.build(text=', comida')
        mock_resp = _mock_response(_mock_meal())

        with patch(
            'bot.domain.commands.meal_recipes.HttpClient.get', return_value=mock_resp
        ) as mock_get:
            await command.run(data)

            mock_get.assert_called_once_with('https://www.themealdb.com/api/json/v1/1/random.php')

    @pytest.mark.anyio
    async def test_returns_image_with_recipe(self, command):
        data = GroupCommandDataFactory.build(text=', comida')
        mock_resp = _mock_response(_mock_meal())

        with patch('bot.domain.commands.meal_recipes.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        assert len(messages) == 1
        assert isinstance(messages[0].content, ImageContent)
        assert messages[0].content.url == 'https://example.com/meal.jpg'
        caption = messages[0].content.caption
        assert 'Spaghetti Bolognese' in caption
        assert 'Italian' in caption
        assert 'Spaghetti' in caption
        assert '200g' in caption
        assert 'Cook the pasta' in caption

    @pytest.mark.anyio
    async def test_includes_ingredients_list(self, command):
        data = GroupCommandDataFactory.build(text=', comida')
        meal = _mock_meal()
        mock_resp = _mock_response(meal)

        with patch('bot.domain.commands.meal_recipes.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert '- Spaghetti | 200g' in caption
        assert '- Tomato | 3' in caption

    @pytest.mark.anyio
    async def test_stops_at_empty_ingredient(self, command):
        data = GroupCommandDataFactory.build(text=', comida')
        meal = _mock_meal()
        mock_resp = _mock_response(meal)

        with patch('bot.domain.commands.meal_recipes.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        caption = messages[0].content.caption
        # Should only have 2 ingredients (strIngredient3 is empty)
        assert caption.count('- ') == 2

    @pytest.mark.anyio
    async def test_handles_missing_optional_fields(self, command):
        data = GroupCommandDataFactory.build(text=', comida')
        meal = _mock_meal(strArea=None, strTags=None, strYoutube=None, strSource=None)
        mock_resp = _mock_response(meal)

        with patch('bot.domain.commands.meal_recipes.HttpClient.get', return_value=mock_resp):
            messages = await command.run(data)

        caption = messages[0].content.caption
        assert 'Sem País' in caption
