import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

export default class YugiohCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*ygo\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma carta aleatória de Yu-Gi-Oh!.';

  async run(data: CommandData): Promise<Message[]> {
    const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
    const response = await AxiosClient.get<{
      data: { card_images: { image_url: string }[]; desc: string; name: string }[];
    }>(url);
    const card = response.data['data'][0];
    const card_image = card.card_images[0].image_url;
    card.desc = card.desc.replace(/\n/g, '');

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: {
          viewOnce: !data.text.match(/show/),
          image: { url: card_image },
          caption: `*${card.name}*\n\n> ${card.desc}`,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
