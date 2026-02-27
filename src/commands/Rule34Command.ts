import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import axios from 'axios';
import * as cheerio from 'cheerio';

export default class Rule34Command extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*rule\\s*34\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba uma imagem aleatória da Rule 34.';

  async run(data: CommandData): Promise<Message[]> {
    const TIMEOUT = 30000;

    const response = await axios.get('https://rule34.xxx/index.php?page=post&s=random', {
      timeout: TIMEOUT,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        Connection: 'keep-alive',
      },
    });

    const $ = cheerio.load(response.data);
    const images: { src: string }[] = [];

    $('div.flexi img').each((i, elem) => {
      const src = $(elem).attr('src');
      if (src) {
        images.push({ src });
      }
    });

    if (images.length === 0) {
      throw new Error('Nenhuma imagem encontrada');
    }

    const banner_url = 'https://kanako.store/products/futa-body';
    const url =
      images[0]['src'] === banner_url && images.length > 1 ? images[1]['src'] : images[0]['src'];

    if (!url) {
      throw new Error('URL da imagem inválida');
    }

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
          image: { url: url },
          caption: 'Aqui está a imagem que você pediu 🤗',
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
