import axios from 'axios';
import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;

export default class MealRecipesCommand {

    static identifier = "^\\s*\\,\\s*comida\\s*$";

    static async run(data) {
        console.log('MEAL RECIPES COMMAND');

        const chat = await data.getChat();
        const url = 'https://www.themealdb.com/api/json/v1/1/random.php';
        try {
            const response = await axios.get(url);
            const meal = response.data.meals[0];
            console.log('meal', meal);

            let caption = '';
            caption += `*${meal.strMeal}*\n\n`;
            caption += `🗺️ ${meal.strArea || 'Sem País'}\n`;
            caption += `🍽️ ${meal.strCategory|| ''} ${meal.strTags || ''}\n`;
            caption += '\n🍲 Ingredientes:\n';
            for (let i = 1; i <= 20; i++) {
                const ingredient = meal[`strIngredient${i}`];
                const measure = meal[`strMeasure${i}`];
                if (!ingredient) break;
                caption += `- ${ingredient} | ${measure}\n`;
            }
            caption += `\n📝 Passo a passo:\n`
            caption += `${meal.strInstructions}\n\n`;
            caption += `📸 ${meal.strMealThumb}\n`;
            caption += `🎥 ${meal.strYoutube}\n`;
            caption += `🔗 ${meal.strSource}\n`;
            await chat.sendMessage(
                caption,
                // await MessageMedia.fromUrl(meal.strMealThumb),
                {
                    sendSeen: true,
                    caption: caption,
                    linkPreview: false,
                    quotedMessageId: data.id._serialized
                }
            );
        }
        catch (error) {
            console.error('ERROR MEAL RECIPES COMMAND', error);

            chat.sendMessage(
                'Viiixxiii... Não consegui baixar te dar uma comida! 🥺👉👈',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
    }
}