import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

export default class MealRecipesCommand extends Command {
  readonly config: CommandConfig = {
    name: 'comida',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba aleatoriamente uma receita e suas instruções em inglês.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const url = 'https://www.themealdb.com/api/json/v1/1/random.php';
    const response = await AxiosClient.get<{ meals: Record<string, string>[] }>(url);
    const meal = response.data.meals[0];

    let caption = '';
    caption += `*${meal.strMeal}*\n\n`;
    caption += `🗺️ ${meal.strArea || 'Sem País'}\n`;
    caption += `🍽️ ${meal.strCategory || ''} ${meal.strTags || ''}\n`;
    caption += '\n🍲 Ingredientes:\n';
    for (let i = 1; i <= 20; i++) {
      const ingredient = meal[`strIngredient${i}`];
      const measure = meal[`strMeasure${i}`];
      if (!ingredient) {
        break;
      }
      caption += `- ${ingredient} | ${measure}\n`;
    }
    caption += `\n📝 Passo a passo:\n`;
    caption += `${meal.strInstructions}\n\n`;
    caption += `🎥 ${meal.strYoutube}\n`;
    caption += `🔗 ${meal.strSource}\n`;
    return [Reply.to(data).image(meal.strMealThumb, caption)];
  }
}
