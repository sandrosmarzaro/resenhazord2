import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import * as cheerio from 'cheerio';
import Reply from '../builders/Reply.js';

export default class Rule34Command extends Command {
  readonly config: CommandConfig = {
    name: 'rule 34',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba uma imagem aleatória da Rule 34.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const TIMEOUT = 30000;

    const response = await AxiosClient.get('https://rule34.xxx/index.php?page=post&s=random', {
      timeout: TIMEOUT,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        Connection: 'keep-alive',
      },
    });

    const $ = cheerio.load(response.data as string);
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

    return [Reply.to(data).image(url, 'Aqui está a imagem que você pediu 🤗')];
  }
}
