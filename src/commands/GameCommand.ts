import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import Reply from '../builders/Reply.js';
import AxiosClient from '../infra/AxiosClient.js';
import IgdbService from '../clients/IgdbService.js';

interface GameInfo {
  name: string;
  year: string;
  genres: string;
  platforms: string;
  rating: string | null;
  coverUrl: string;
}

interface GameSource {
  fetch(): Promise<GameInfo>;
}

interface RawgPlatform {
  platform: { name: string };
}

interface RawgGenre {
  name: string;
}

interface RawgGame {
  name: string;
  released?: string;
  background_image?: string;
  metacritic?: number;
  genres: RawgGenre[];
  platforms?: RawgPlatform[];
}

interface RawgResponse {
  results: RawgGame[];
}

class IgdbSource implements GameSource {
  async fetch(): Promise<GameInfo> {
    const game = await IgdbService.getRandomGame();
    const year = game.first_release_date
      ? String(new Date(game.first_release_date * 1000).getFullYear())
      : '?';
    const genres = game.genres?.map((g) => g.name).join(', ') || '—';
    const platforms = game.platforms?.map((p) => p.name).join(', ') || '—';
    const rating = game.total_rating ? `${Math.round(game.total_rating)}/100` : null;
    return {
      name: game.name,
      year,
      genres,
      platforms,
      rating,
      coverUrl: IgdbService.coverUrl(game.cover.image_id),
    };
  }
}

class RawgSource implements GameSource {
  async fetch(): Promise<GameInfo> {
    const page = Math.floor(Math.random() * 200) + 1;
    const response = await AxiosClient.get<RawgResponse>('https://api.rawg.io/api/games', {
      params: {
        key: process.env.RAWG_API_KEY ?? '',
        ordering: '-metacritic',
        page_size: 40,
        page,
      },
    });
    const games = response.data.results.filter((g) => g.background_image);
    if (games.length === 0) throw new Error('No games with images found');
    const game = games[Math.floor(Math.random() * games.length)];
    const year = game.released?.slice(0, 4) ?? '?';
    const genres = game.genres.map((g) => g.name).join(', ') || '—';
    const platforms = game.platforms?.map((p) => p.platform.name).join(', ') || '—';
    const rating = game.metacritic ? `${game.metacritic}/100` : null;
    return { name: game.name, year, genres, platforms, rating, coverUrl: game.background_image! };
  }
}

function buildCaption(game: GameInfo): string {
  const lines = [
    `🎮 *${game.name}* (${game.year})`,
    '',
    `🏷️ ${game.genres}`,
    `🖥️ ${game.platforms}`,
  ];
  if (game.rating) lines.push(`⭐ ${game.rating}`);
  return lines.join('\n');
}

export default class GameCommand extends Command {
  readonly config: CommandConfig = {
    name: 'game',
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba um jogo aleatório com capa e informações.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const sources: GameSource[] = [new IgdbSource(), new RawgSource()];
    for (const source of sources) {
      try {
        const game = await source.fetch();
        return [Reply.to(data).image(game.coverUrl, buildCaption(game))];
      } catch {
        continue;
      }
    }
    return [Reply.to(data).text('Erro ao buscar jogo. Tente novamente mais tarde! 🎮')];
  }
}
