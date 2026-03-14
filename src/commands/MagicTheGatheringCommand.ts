import CardBoosterCommand, { type BoosterConfig, type CardItem } from './CardBoosterCommand.js';
import {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

interface MTGCard {
  name: string;
  text: string;
  imageUrl?: string;
}

export default class MagicTheGatheringCommand extends CardBoosterCommand {
  readonly config: CommandConfig = {
    name: 'mtg',
    flags: ['booster', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória de Magic: The Gathering.';

  protected readonly boosterConfig: BoosterConfig = {
    flagName: 'booster',
    count: 6,
    columns: 3,
    cellWidth: 300,
    cellHeight: 420,
    shim: 0,
    shimBackground: '#ffffff',
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  };

  private static readonly API_URL = 'https://api.magicthegathering.io/v1/cards';
  private static readonly PAGE_SIZE = 100;
  private static readonly MAX_RETRIES = 5;

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('booster')) {
      return this.runBooster(data);
    }
    const total_pages = await this.fetchTotalPages();
    const card = await this.fetchSingleCard(total_pages);
    const caption = `*${card.name}*\n\n> ${card.text ?? ''}`;
    return [Reply.to(data).image(card.imageUrl!, caption)];
  }

  protected async fetchBoosterItems(): Promise<CardItem[]> {
    const total_pages = await this.fetchTotalPages();
    return Promise.all(
      Array.from({ length: this.boosterConfig.count }, async () => {
        const card = await this.fetchSingleCard(total_pages);
        return { imageUrl: card.imageUrl!, label: card.name };
      }),
    );
  }

  private async fetchTotalPages(): Promise<number> {
    const response = await AxiosClient.get(
      `${MagicTheGatheringCommand.API_URL}?pageSize=${MagicTheGatheringCommand.PAGE_SIZE}`,
    );
    const total_cards = parseInt(response.headers['total-count']);
    return Math.ceil(total_cards / MagicTheGatheringCommand.PAGE_SIZE);
  }

  private async fetchSingleCard(total_pages: number): Promise<MTGCard & { imageUrl: string }> {
    for (let attempt = 0; attempt < MagicTheGatheringCommand.MAX_RETRIES; attempt++) {
      const random_page = Math.floor(Math.random() * total_pages) + 1;
      const response = await AxiosClient.get<{ cards: MTGCard[] }>(
        `${MagicTheGatheringCommand.API_URL}?pageSize=${MagicTheGatheringCommand.PAGE_SIZE}&page=${random_page}`,
      );
      const candidates = response.data.cards.filter(
        (c): c is MTGCard & { imageUrl: string } =>
          Boolean(c.imageUrl) && !c.imageUrl!.includes('multiverseid=0'),
      );
      if (!candidates.length) continue;
      const card = candidates[Math.floor(Math.random() * candidates.length)];
      // Some valid-looking URLs redirect to the card back for cards without a digital scan.
      // Follow the redirect and skip cards that resolve to card_back.
      const headRes = await fetch(card.imageUrl, { method: 'HEAD' });
      if (!headRes.url.includes('card_back')) return card;
    }
    throw new Error('MTG: no card with image after retries');
  }
}
