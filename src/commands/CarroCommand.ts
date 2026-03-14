import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import { FIPE_BRANDS } from '../data/carBrands.js';
import { Sentry } from '../infra/Sentry.js';

interface FipeModels {
  modelos: Array<{ codigo: number; nome: string }>;
}

interface FipeYear {
  codigo: string;
  nome: string;
}

interface FipeDetails {
  Marca: string;
  Modelo: string;
  AnoModelo: number;
  Combustivel: string;
  Valor: string;
}

interface WikiPage {
  title?: string;
  thumbnail?: { source: string };
}

interface WikiQueryResponse {
  query?: { pages?: Record<string, WikiPage> };
}

export default class CarroCommand extends Command {
  readonly config: CommandConfig = {
    name: 'carro',
    flags: ['show', 'dm', 'wiki'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba a foto de um carro aleatório com modelo, ano e preço FIPE.';

  private static readonly FIPE_BASE = 'https://parallelum.com.br/fipe/api/v1/carros/marcas';
  private static readonly WIKI_API = 'https://en.wikipedia.org/w/api.php';
  private static readonly COMMONS_API = 'https://commons.wikimedia.org/w/api.php';
  private static readonly WIKI_UA =
    'ResenhazordBot/2.0 (https://github.com/smarzaro/resenhazord2; bot@resenhazord.com)';
  private static readonly FIPE_OPTS = { retries: 0, timeout: 8000 };
  private static readonly WIKI_OPTS = {
    retries: 0,
    timeout: 8000,
    headers: { 'User-Agent': CarroCommand.WIKI_UA },
  };
  private static readonly IMG_TIMEOUT = {
    timeout: 12000,
    headers: { 'User-Agent': CarroCommand.WIKI_UA },
  };

  private static pick<T>(arr: T[]): T {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // Strip engine/trim specs — keep words before first spec token
  // e.g. "911 Targa 4S 3.0 420cv (991)" → "911 Targa 4S", "Tiggo 5X SPORT 1.5 Turbo" → "Tiggo 5X SPORT"
  private static baseModelName(nome: string): string {
    const SPEC_TOKEN = /^\d+\.\d|^\d+[pP]$|\d+cv$/i;
    const SPEC_WORD = new Set(['flex', 'gasolina', 'diesel', 'aut.', 'mec.', 'cvt', 'turbo']);
    const words = nome.trim().split(/\s+/);
    const stop = words.findIndex((w) => SPEC_TOKEN.test(w) || SPEC_WORD.has(w.toLowerCase()));
    return (stop > 0 ? words.slice(0, stop) : words).join(' ');
  }

  // Aggressive strip for Wikipedia search — removes body styles and trim designations
  // e.g. "Civic Sedan LX/LXL 1.7 16V" → "Civic", "Palio Weekend Adv. Ext." → "Palio Weekend"
  private static wikiModelName(nome: string): string {
    const SPEC_TOKEN = /^\d+\.\d|^\d+[pP]$|\d+cv$/i;
    const SPEC_WORD = new Set([
      // Fuel/transmission
      'flex',
      'gasolina',
      'diesel',
      'aut',
      'mec',
      'cvt',
      'turbo',
      // Body styles
      'sedan',
      'hatch',
      'sw',
      'furgão',
      'furgao',
      'cabine',
      'pickup',
      // Trim designations
      'dlx',
      'lx',
      'lxl',
      'ex',
      'elx',
      'glx',
      'gls',
      'gli',
      'vip',
      'luxury',
      'elite',
      'premium',
      'limited',
      'sport',
      'comfort',
      'exclusive',
      'country',
      'land',
      'adv',
      'ext',
      'adventure',
    ]);
    const words = nome
      .trim()
      .split(/\s+/)
      .flatMap((t) => t.split('/'));
    const stop = words.findIndex((w) => {
      const clean = w.replace(/[.,]+$/, '').toLowerCase();
      return SPEC_TOKEN.test(w) || SPEC_WORD.has(clean);
    });
    return (stop > 0 ? words.slice(0, stop) : words).join(' ');
  }

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    try {
      const brand = CarroCommand.pick(FIPE_BRANDS);
      const base = `${CarroCommand.FIPE_BASE}/${brand.fipeCode}`;

      const modelsRes = await AxiosClient.get<FipeModels>(
        `${base}/modelos`,
        CarroCommand.FIPE_OPTS,
      );
      const model = CarroCommand.pick(modelsRes.data.modelos);

      const yearsRes = await AxiosClient.get<FipeYear[]>(
        `${base}/modelos/${model.codigo}/anos`,
        CarroCommand.FIPE_OPTS,
      );
      // Retry up to 3 different years — some codes return FIPE error
      let details: FipeDetails | null = null;
      const years = [...yearsRes.data].sort(() => Math.random() - 0.5);
      for (const year of years.slice(0, 3)) {
        const res = await AxiosClient.get<FipeDetails | { error: string }>(
          `${base}/modelos/${model.codigo}/anos/${year.codigo}`,
          CarroCommand.FIPE_OPTS,
        );
        if (!('error' in res.data)) {
          details = res.data as FipeDetails;
          break;
        }
      }

      const caption = details
        ? [
            `${brand.emoji} *${details.Marca} ${details.Modelo}*`,
            `📅 ${details.AnoModelo} | ⛽ ${details.Combustivel}`,
            `💰 ${details.Valor}`,
            brand.origin,
          ].join('\n')
        : `${brand.emoji} *${brand.name} ${model.nome}*\n${brand.origin}`;

      const baseName = CarroCommand.baseModelName(model.nome);
      const wikiName = CarroCommand.wikiModelName(model.nome);
      const searchTerm = encodeURIComponent(`${brand.name} ${wikiName} car`);
      const wikiUrl =
        `${CarroCommand.WIKI_API}?action=query&generator=search` +
        `&gsrsearch=${searchTerm}&gsrlimit=1&prop=pageimages&pithumbsize=640&format=json`;
      const wikiRes = await AxiosClient.get<WikiQueryResponse>(wikiUrl, CarroCommand.WIKI_OPTS);

      const pages = wikiRes.data.query?.pages;
      const firstPage = Object.values(pages ?? {})[0];
      const pageTitle = firstPage?.title ?? '';
      const rawThumb = firstPage?.thumbnail?.source;

      const brandLower = brand.name.toLowerCase();
      const titleLower = pageTitle.toLowerCase();
      const isBrandOnly =
        (pageTitle !== '' && titleLower === brandLower) ||
        new RegExp(
          `^${brandLower.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s+(?:motors?|automobiles?|automotive|group|corporation)$`,
          'i',
        ).test(titleLower);

      let thumb = isBrandOnly ? undefined : rawThumb;

      if (!thumb && !parsed.flags.has('wiki')) {
        const commonsSearch = encodeURIComponent(`${brand.name} ${baseName}`);
        const commonsUrl =
          `${CarroCommand.COMMONS_API}?action=query&generator=search` +
          `&gsrsearch=${commonsSearch}&gsrnamespace=6&gsrlimit=1` +
          `&prop=pageimages&pithumbsize=640&format=json`;
        const commonsRes = await AxiosClient.get<WikiQueryResponse>(
          commonsUrl,
          CarroCommand.WIKI_OPTS,
        );
        const commonsPages = commonsRes.data.query?.pages;
        thumb = Object.values(commonsPages ?? {})[0]?.thumbnail?.source;
      }

      if (!thumb) {
        return [Reply.to(data).text(caption)];
      }

      const buffer = await AxiosClient.getBuffer(thumb, CarroCommand.IMG_TIMEOUT);
      return [Reply.to(data).imageBuffer(buffer, caption)];
    } catch (error) {
      Sentry.captureException(error, { extra: { command: 'carro' } });
      return [Reply.to(data).text('Erro ao buscar carro. Tente novamente mais tarde! 🚗')];
    }
  }
}
