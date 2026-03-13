import * as cheerio from 'cheerio';
import AxiosClient from '../infra/AxiosClient.js';
import { ANIMAL_EMOJIS } from '../data/bichoAnimalEmojis.js';
import { DRAWS } from '../data/bichoDraws.js';

export { DRAWS };

export interface DrawPrize {
  prize: number;
  milhar: string;
  animal: string;
  group: number;
  emoji: string;
}

export interface DrawResult {
  id: string;
  label: string;
  published: boolean;
  prizes: DrawPrize[];
}

export default class BichoScraper {
  private static readonly url = 'https://eojogodobicho.com/deu-no-poste.html';

  static async fetch(): Promise<DrawResult[]> {
    const response = await AxiosClient.get<string>(BichoScraper.url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      },
    });

    const $ = cheerio.load(response.data);

    return DRAWS.map(({ id, label }) => {
      const block = $(`#bloco-${id}`);
      const published = block.find('.status-publicado').length > 0;
      const prizes: DrawPrize[] = [];

      if (published) {
        block.find('table.dnp-table tbody tr').each((i, row) => {
          const milhar = $(row).find('td.dnp-milhar').text().trim();
          const groupText = $(row).find('td:nth-child(3) a').text().trim();
          const animal = $(row).find('td:last-child a').text().trim();
          const group = parseInt(groupText, 10);
          const emoji = ANIMAL_EMOJIS[animal] ?? '🐾';

          if (milhar && animal && !isNaN(group)) {
            prizes.push({ prize: i + 1, milhar, animal, group, emoji });
          }
        });
      }

      return { id, label, published, prizes };
    });
  }
}
