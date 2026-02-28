import AxiosClient from '../infra/AxiosClient.js';
import * as cheerio from 'cheerio';

interface XVideosResult {
  videoUrl: string;
  title: string;
}

export default class XVideosScraper {
  private static readonly HEADERS = {
    'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    Connection: 'keep-alive',
  };

  private static readonly TIMEOUT = 30000;
  private static readonly MAX_PAGE = 50;

  static async getRandomVideo(): Promise<XVideosResult> {
    const page = Math.floor(Math.random() * this.MAX_PAGE) + 1;
    const listingUrl = `https://www.xvideos.com/new/${page}`;

    const listingResponse = await AxiosClient.get<string>(listingUrl, {
      timeout: this.TIMEOUT,
      headers: this.HEADERS,
    });

    const $ = cheerio.load(listingResponse.data);
    const videoLinks: string[] = [];

    $('div.thumb-block a[href^="/video"]').each((_i, elem) => {
      const href = $(elem).attr('href');
      if (href && !videoLinks.includes(href)) {
        videoLinks.push(href);
      }
    });

    if (videoLinks.length === 0) {
      throw new Error('Nenhum vídeo encontrado na listagem');
    }

    const randomLink = videoLinks[Math.floor(Math.random() * videoLinks.length)];
    const videoPageUrl = `https://www.xvideos.com${randomLink}`;

    const videoResponse = await AxiosClient.get<string>(videoPageUrl, {
      timeout: this.TIMEOUT,
      headers: this.HEADERS,
    });

    const html = videoResponse.data;

    const titleMatch = html.match(/<title>([^<]+)<\/title>/);
    const title = titleMatch ? titleMatch[1].replace(/ - XVIDEOS\.COM$/, '').trim() : 'Vídeo';

    const lowMatch = html.match(/setVideoUrlLow\('([^']+)'\)/);
    const highMatch = html.match(/setVideoUrlHigh\('([^']+)'\)/);
    const videoUrl = lowMatch?.[1] ?? highMatch?.[1];

    if (!videoUrl) {
      throw new Error('Não foi possível extrair URL do vídeo');
    }

    return { videoUrl, title };
  }
}
