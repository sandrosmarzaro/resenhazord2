import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

export default class YugiohCommand extends Command {
  readonly config: CommandConfig = { name: 'ygo', flags: ['show', 'dm'], category: 'aleatórias' };
  readonly menuDescription = 'Receba uma carta aleatória de Yu-Gi-Oh!.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
    const response = await AxiosClient.get<{
      data: { card_images: { image_url: string }[]; desc: string; name: string }[];
    }>(url);
    const card = response.data['data'][0];
    const card_image = card.card_images[0].image_url;
    card.desc = card.desc.replace(/\n/g, '');

    return [Reply.to(data).image(card_image, `*${card.name}*\n\n> ${card.desc}`)];
  }
}
