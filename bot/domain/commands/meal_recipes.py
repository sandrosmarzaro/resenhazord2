from bot.domain.builders.reply import Reply
from bot.domain.commands.base import Command, CommandConfig, ParsedCommand
from bot.domain.models.command_data import CommandData
from bot.domain.models.message import BotMessage
from bot.infrastructure.http_client import HttpClient


class MealRecipesCommand(Command):
    MAX_INGREDIENTS = 20

    @property
    def config(self) -> CommandConfig:
        return CommandConfig(
            name='comida',
            aliases=['food'],
            flags=['show', 'dm'],
            category='aleatórias',
        )

    @property
    def menu_description(self) -> str:
        return 'Receba aleatoriamente uma receita e suas instruções em inglês.'

    async def execute(self, data: CommandData, parsed: ParsedCommand) -> list[BotMessage]:
        url = 'https://www.themealdb.com/api/json/v1/1/random.php'
        response = await HttpClient.get(url)
        response.raise_for_status()
        meal = response.json()['meals'][0]

        caption = f'*{meal["strMeal"]}*\n\n'
        caption += f'🗺️ {meal.get("strArea") or "Sem País"}\n'
        caption += f'🍽️ {meal.get("strCategory") or ""} {meal.get("strTags") or ""}\n'
        caption += '\n🍲 Ingredientes:\n'
        for i in range(1, self.MAX_INGREDIENTS + 1):
            ingredient = meal.get(f'strIngredient{i}')
            if not ingredient:
                break
            measure = meal.get(f'strMeasure{i}') or ''
            caption += f'- {ingredient} | {measure}\n'
        caption += '\n📝 Passo a passo:\n'
        caption += f'{meal["strInstructions"]}\n\n'
        caption += f'🎥 {meal.get("strYoutube") or ""}\n'
        caption += f'🔗 {meal.get("strSource") or ""}\n'
        return [Reply.to(data).image(meal['strMealThumb'], caption)]
