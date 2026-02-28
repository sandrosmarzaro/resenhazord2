import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

export default class BaralhoCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*carta\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma carta de baralho aleatória.';

  async run(data: CommandData): Promise<Message[]> {
    const API_URL = 'https://deckofcardsapi.com/api/deck/new/draw/?count=1';
    const response = await AxiosClient.get<{ cards: { image: string }[] }>(API_URL);
    const card = response.data.cards[0];
    const caption = 'Era essa sua carta? 😏';

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: {
          image: { url: card.image },
          caption: caption,
          viewOnce: !data.text.match(/show/),
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
