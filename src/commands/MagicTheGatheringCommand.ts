import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

export default class MagicTheGatheringCommand extends Command {
  readonly config: CommandConfig = { name: 'mtg', flags: ['show', 'dm'] };
  readonly menuDescription = 'Receba uma carta aleatória de Magic: The Gathering.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const API_URL = 'https://api.magicthegathering.io/v1/cards';
    const PAGE_SIZE = 100;
    const initial_response = await AxiosClient.get(`${API_URL}?pageSize=${PAGE_SIZE}`);

    const total_cards = parseInt(initial_response.headers['total-count']);
    const total_tages = Math.ceil(total_cards / PAGE_SIZE);

    const random_page = Math.floor(Math.random() * total_tages) + 1;

    const page_response = await AxiosClient.get<{
      cards: { name: string; text: string; imageUrl: string }[];
    }>(`${API_URL}?pageSize=${PAGE_SIZE}&page=${random_page}`);
    const cards_on_page = page_response.data.cards;

    const card = cards_on_page[Math.floor(Math.random() * cards_on_page.length)];
    const caption = `*${card.name}*\n\n> ${card.text}`;

    return [Reply.to(data).image(card.imageUrl, caption)];
  }
}
