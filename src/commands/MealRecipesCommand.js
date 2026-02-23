import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class MealRecipesCommand {
  static identifier = '^\\s*\\,\\s*comida\\s*$';

  static async run(data) {
    const url = 'https://www.themealdb.com/api/json/v1/1/random.php';
    await axios
      .get(url)
      .then(async (response) => {
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
        await Resenhazord2.socket.sendMessage(
          data.key.remoteJid,
          {
            caption: caption,
            linkPreview: false,
            image: { url: meal.strMealThumb },
          },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      })
      .catch(async (error) => {
        console.log(`ERROR MEAL RECIPES COMMAND\n${error}`);
        await Resenhazord2.socket.sendMessage(
          data.key.remoteJid,
          { text: 'Viiixxiii... Não consegui te dar uma comida! 🥺👉👈' },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      });
  }
}
