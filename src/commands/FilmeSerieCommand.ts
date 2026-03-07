import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

export default class FilmeSerieCommand extends Command {
  readonly config: CommandConfig = {
    name: 'filme',
    aliases: ['série'],
    options: [{ name: 'mode', values: ['top', 'pop'] }],
    flags: ['show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription =
    'Receba aleatoriamente um filme ou série top 500 em popularidade ou por nota.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const type = parsed.commandName === 'filme' ? 'movie' : 'tv';
    const modeValue = parsed.options.get('mode');
    const mode = modeValue === 'top' ? 'top_rated' : 'popular';
    const url = `https://api.themoviedb.org/3/${type}/${mode}`;

    const page = Math.floor(Math.random() * 25) + 1;
    interface MovieResult {
      poster_path: string;
      genre_ids: number[];
      release_date?: string;
      first_air_date?: string;
      title?: string;
      name?: string;
      vote_average?: number;
      overview: string;
    }
    const response = await AxiosClient.get<{ results: MovieResult[] }>(url, {
      params: {
        api_key: process.env.TMDB_API_KEY!,
        language: 'pt-BR',
        page: page,
      },
    });
    const jobs = response.data.results;
    const job = jobs[Math.floor(Math.random() * jobs.length)];
    const poster_url = `https://image.tmdb.org/t/p/w500${job.poster_path}`;

    const genres_url = `https://api.themoviedb.org/3/genre/${type}/list`;
    const genres_response = await AxiosClient.get<{ genres: { id: number; name: string }[] }>(
      genres_url,
      {
        params: {
          api_key: process.env.TMDB_API_KEY!,
          language: 'pt-BR',
        },
      },
    );
    const { genres } = genres_response.data;
    const genres_names = job.genre_ids
      .map(
        (id: number) => genres.find((genre: { id: number; name: string }) => genre.id === id)!.name,
      )
      .join(', ');

    const year = type === 'movie' ? job.release_date?.slice(0, 4) : job.first_air_date?.slice(0, 4);
    const name = type === 'movie' ? job.title : job.name;

    let caption = '';
    caption += `*${name}*\n\n`;
    caption += `🧬 ${genres_names}\n`;
    caption += `⭐ ${job.vote_average || 'Sem Nota'}\t📅 ${year || 'Sem Data'}\n\n`;
    caption += `> ${job.overview}`;

    return [Reply.to(data).image(poster_url, caption)];
  }
}
