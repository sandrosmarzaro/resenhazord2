import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import axios from 'axios';

export default class MagicTheGatheringCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*mtg\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma carta aleatória de Magic: The Gathering.';

  async run(data: CommandData): Promise<Message[]> {
    const API_URL = 'https://api.magicthegathering.io/v1/cards';
    const PAGE_SIZE = 100;
    const initial_response = await axios.get(`${API_URL}?pageSize=${PAGE_SIZE}`);

    const total_cards = parseInt(initial_response.headers['total-count']);
    const total_tages = Math.ceil(total_cards / PAGE_SIZE);

    const random_page = Math.floor(Math.random() * total_tages) + 1;

    const page_response = await axios.get(`${API_URL}?pageSize=${PAGE_SIZE}&page=${random_page}`);
    const cards_on_page = page_response.data.cards;

    const card = cards_on_page[Math.floor(Math.random() * cards_on_page.length)];
    const caption = `*${card.name}*\n\n> ${card.text}`;

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: {
          image: { url: card.imageUrl },
          caption: caption,
          viewOnce: !data.text.match(/show/),
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
