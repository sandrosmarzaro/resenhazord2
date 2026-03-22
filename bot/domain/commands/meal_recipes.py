import structlog

from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
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
            flags=['show', 'dm'],
            category='random',
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

        area = meal.get('strArea') or 'Sem País'
        category = meal.get('strCategory') or ''
        tags = meal.get('strTags') or ''
        meta = f'🗺️ {area}   🍽️ {category}'
        if tags:
            meta += f'   🏷️ {tags}'

        instructions_pt = await Translator.to_pt(meal['strInstructions'])

        caption = f'*{meal["strMeal"]}*\n\n'
        caption += f'{meta}\n'
        caption += '\n🍲 Ingredientes:\n'
        for i in range(1, self.MAX_INGREDIENTS + 1):
            ingredient = meal.get(f'strIngredient{i}')
            if not ingredient:
                break
            measure = meal.get(f'strMeasure{i}') or ''
            caption += f'- {ingredient} | {measure}\n'
        caption += '\n📝 Passo a passo:\n'
        caption += f'{instructions_pt}\n'
        youtube = meal.get('strYoutube')
        source = meal.get('strSource')
        if youtube:
            caption += f'\n🎥 {youtube}'
        if source:
            caption += f'\n🔗 {source}'
        return [Reply.to(data).image(meal['strMealThumb'], caption)]
