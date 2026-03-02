import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

export default class BaralhoCommand extends Command {
  readonly config: CommandConfig = { name: 'carta', flags: ['show', 'dm'] };
  readonly menuDescription = 'Receba uma carta de baralho aleatória.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const API_URL = 'https://deckofcardsapi.com/api/deck/new/draw/?count=1';
    const response = await AxiosClient.get<{ cards: { image: string }[] }>(API_URL);
    const card = response.data.cards[0];
    const caption = 'Era essa sua carta? 😏';

    return [
      {
        jid: data.key.remoteJid!,
        content: {
          image: { url: card.image },
          caption: caption,
          viewOnce: true,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
