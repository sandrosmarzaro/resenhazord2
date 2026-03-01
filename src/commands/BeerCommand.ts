import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import OpenFoodFactsScraper from '../services/OpenFoodFactsScraper.js';

export default class BeerCommand extends Command {
  readonly regexIdentifier = '^\\s*,\\s*cerveja\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma cerveja aleatória com imagem.';

  async run(data: CommandData): Promise<Message[]> {
    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }

    try {
      const beer = await OpenFoodFactsScraper.getRandomBeer();
      const lines = [`🍺 *${beer.name}*`, `🏭 _${beer.brand}_`];

      const drinkParts: string[] = [];
      if (beer.alcohol != null) drinkParts.push(`${beer.alcohol}%`);
      if (beer.quantity) drinkParts.push(beer.quantity);
      if (drinkParts.length > 0) lines.push(`🍷 ${drinkParts.join(' · ')}`);

      if (beer.origin) lines.push(`📍 _${beer.origin}_`);
      if (beer.soldIn) lines.push(`🌍 _${beer.soldIn}_`);
      if (beer.ingredients) lines.push(`\n> ${beer.ingredients}`);

      const caption = lines.join('\n');

      return [
        {
          jid: chat_id,
          content: {
            viewOnce: !data.text.match(/show/),
            caption,
            image: { url: beer.imageUrl },
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch {
      return [
        {
          jid: chat_id,
          content: { text: 'Erro ao buscar cerveja. Tente novamente mais tarde! 🍺' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }
}
