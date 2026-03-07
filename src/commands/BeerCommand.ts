import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import OpenFoodFactsScraper from '../services/OpenFoodFactsScraper.js';
import Reply from '../builders/Reply.js';

export default class BeerCommand extends Command {
  readonly config: CommandConfig = { name: 'cerveja', flags: ['show', 'dm'] };
  readonly menuDescription = 'Receba uma cerveja aleatória com imagem.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
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

      return [Reply.to(data).image(beer.imageUrl, caption)];
    } catch {
      return [Reply.to(data).text('Erro ao buscar cerveja. Tente novamente mais tarde! 🍺')];
    }
  }
}
