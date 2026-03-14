import CardBoosterCommand, { type BoosterConfig, type CardItem } from './CardBoosterCommand.js';
import {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

interface YugiohCard {
  name: string;
  desc: string;
  card_images: { image_url: string }[];
}

export default class YugiohCommand extends CardBoosterCommand {
  readonly config: CommandConfig = {
    name: 'ygo',
    flags: ['booster', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma carta aleatória de Yu-Gi-Oh!.';

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

  private static readonly URL = 'https://db.ygoprodeck.com/api/v7/randomcard.php';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('booster')) {
      return this.runBooster(data);
    }
    const response = await AxiosClient.get<{ data: YugiohCard[] }>(YugiohCommand.URL);
    const card = response.data['data'][0];
    const card_image = card.card_images[0].image_url;
    card.desc = card.desc.replace(/\n/g, '');
    return [Reply.to(data).image(card_image, `*${card.name}*\n\n> ${card.desc}`)];
  }

  protected async fetchBoosterItems(): Promise<CardItem[]> {
    const responses = await Promise.all(
      Array.from({ length: this.boosterConfig.count }, () =>
        AxiosClient.get<{ data: YugiohCard[] }>(YugiohCommand.URL),
      ),
    );
    return responses.map((r) => ({
      imageUrl: r.data['data'][0].card_images[0].image_url,
      label: r.data['data'][0].name,
    }));
  }
}
