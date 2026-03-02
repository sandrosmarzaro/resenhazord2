import type { CommandData } from '../types/command.js';
import type { AnyMessageContent } from '@whiskeysockets/baileys';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

export default class MealRecipesCommand extends Command {
  readonly config: CommandConfig = { name: 'comida' };
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
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          caption: caption,
          image: { url: meal.strMealThumb },
        } as AnyMessageContent,
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
