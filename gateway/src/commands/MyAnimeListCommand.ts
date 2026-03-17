import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import type { AnimeData } from '../types/commands/myanimelist.js';

export default class MyAnimeListCommand extends Command {
  readonly config: CommandConfig = {
    name: 'anime',
    aliases: ['manga'],
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba um anime ou mangá aleatório do top 500 do MyAnimeList.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const base_url = 'https://api.jikan.moe/v4';
    const type = parsed.commandName === 'anime' ? 'anime' : 'manga';
    const page = Math.floor(Math.random() * 20) + 1;

    const response = await AxiosClient.get<{ data: AnimeData[] }>(base_url + `/top/${type}`, {
      params: { page: page },
    });
    const animes = response.data.data;
    const anime = animes[Math.floor(Math.random() * animes.length)];

    const image = anime.images.webp.large_image_url;
    const genres = anime.genres.map((genre: { name: string }) => genre.name).join(', ');
    const themes = anime.themes.map((theme: { name: string }) => theme.name).join(', ');
    const demos = anime.demographics
      .map((demographic: { name: string }) => demographic.name)
      .join(', ');
    let creator_emoji;
    let creators;
    let release_date;
    let size;
    let size_emoji;
    if (type === 'anime') {
      creator_emoji = '🎙️';
      creators = anime.studios?.map((studio) => studio.name).join(', ');
      release_date = anime.aired?.prop.from.year;
      size = anime.episodes;
      size_emoji = '🎥';
    } else {
      creator_emoji = '🖋';
      creators = anime.authors?.map((author) => author.name).join(', ');
      release_date = anime.published?.prop.from.year;
      size = anime.chapters;
      size_emoji = '📚';
    }

    let caption = '';
    caption += `*${anime.title}*\n\n`;
    caption += `${size_emoji} ${size || '?'}x \t📅 ${release_date || '?'}\n`;
    caption += `⭐️ ${anime.score || '?'} \t🏆 #${anime.rank || '?'}\n`;
    caption += `🧬 ${genres || 'Desconhecido'}\n`;
    caption += `📜 ${themes || 'Desconhecido'}\n`;
    caption += `📈 ${demos || 'Desconhecido'}\n`;
    caption += `${creator_emoji} ${creators || 'Desconhecido'}`;

    return [Reply.to(data).image(image, caption)];
  }
}
