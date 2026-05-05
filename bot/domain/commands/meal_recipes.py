import structlog

from bot.data.meal_categories import AREA_PT, CATEGORY_PT
from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Category, Command, CommandConfig, Flag, ParsedCommand, Platform
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.domain.services.translator import Translator
from bot.infrastructure.http_client import HttpClient

logger = structlog.get_logger()


class MealRecipesCommand(Command):
    MAX_INGREDIENTS = 20

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='comida',
            aliases=['food'],
            flags=[Flag.SHOW, Flag.DM],
            category=Category.RANDOM,
            platforms=[Platform.ALL],
        )

    @property
    def menu_description(self) -> str:
        return 'Receba aleatoriamente uma receita e suas instruções.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        try:
            return await self._fetch_and_build(data)
        except Exception:
            logger.exception('meal_recipes_error')
            return [Reply.to(data).text('Erro ao buscar receita. Tente novamente mais tarde! 🍽️')]

    async def _fetch_and_build(self, data: CommandData) -> list[BotMessage]:
        url = 'https://www.themealdb.com/api/json/v1/1/random.php'
        response = await HttpClient.get(url)
        response.raise_for_status()
        meal = response.json()['meals'][0]

        title_pt = await Translator.to_pt(meal['strMeal'])
        instructions_pt = await Translator.to_pt(meal['strInstructions'])
        caption = self._build_caption(meal, title_pt, instructions_pt)
        return [Reply.to(data).image(meal['strMealThumb'], caption)]

    @classmethod
    def _build_caption(cls, meal: dict, title: str, instructions: str) -> str:
        area = cls._localize(meal.get('strArea') or '', AREA_PT, 'Sem País')
        category = cls._localize(meal.get('strCategory') or '', CATEGORY_PT)
        tags = meal.get('strTags') or ''

        meta = f'🗺️ {area}   🍽️ {category}'
        if tags:
            meta += f'   🏷️ {tags}'

        ingredients = cls._build_ingredients(meal)
        links = cls._build_links(meal)

        parts = [
            f'*{title}*',
            '',
            meta,
            '',
            '🍲 Ingredientes:',
            ingredients,
            '',
            '📝 Passo a passo:',
            instructions,
        ]
        if links:
            parts.append(links)
        return '\n'.join(parts)

    @classmethod
    def _build_ingredients(cls, meal: dict) -> str:
        lines: list[str] = []
        for i in range(1, cls.MAX_INGREDIENTS + 1):
            ingredient = meal.get(f'strIngredient{i}')
            if not ingredient:
                break
            measure = meal.get(f'strMeasure{i}') or ''
            lines.append(f'- {ingredient} | {measure}')
        return '\n'.join(lines)

    @staticmethod
    def _localize(value: str, table: dict, fallback: str = '') -> str:
        return table.get(value, value) or fallback

    @staticmethod
    def _build_links(meal: dict) -> str:
        parts: list[str] = []
        youtube = meal.get('strYoutube')
        source = meal.get('strSource')
        if youtube:
            parts.append(f'🎥 {youtube}')
        if source:
            parts.append(f'🔗 {source}')
        return '\n'.join(parts)
