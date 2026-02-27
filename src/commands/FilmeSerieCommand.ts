import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import axios from 'axios';

export default class FilmeSerieCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*(?:filme|s.rie)\\s*(?:top|pop)?\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription =
    'Receba aleatoriamente um filme ou série top 500 em popularidade ou por nota.';

  async run(data: CommandData): Promise<Message[]> {
    const type = data.text.match(/filme/i) ? 'movie' : 'tv';
    const rest_command = data.text.replace(/\s*,(?:filme|serie)\s*\s*/i, '').replace(/\s|\n/, '');
    const mode = rest_command.match(/top/i) ? 'top_rated' : 'popular';
    const url = `https://api.themoviedb.org/3/${type}/${mode}`;

    const page = Math.floor(Math.random() * 25) + 1;
    const response = await axios.get(url, {
      params: {
        api_key: process.env.TMDB_API_KEY,
        language: 'pt-BR',
        page: page,
      },
    });
    const jobs = response.data.results;
    const job = jobs[Math.floor(Math.random() * jobs.length)];
    const poster_url = `https://image.tmdb.org/t/p/w500${job.poster_path}`;

    const genres_url = `https://api.themoviedb.org/3/genre/${type}/list`;
    const genres_response = await axios.get(genres_url, {
      params: {
        api_key: process.env.TMDB_API_KEY,
        language: 'pt-BR',
      },
    });
    const { genres } = genres_response.data;
    const genres_names = job.genre_ids
      .map(
        (id: number) => genres.find((genre: { id: number; name: string }) => genre.id === id)!.name,
      )
      .join(', ');

    const year = type === 'movie' ? job.release_date.slice(0, 4) : job.first_air_date.slice(0, 4);
    const name = type === 'movie' ? job.title : job.name;

    let caption = '';
    caption += `*${name}*\n\n`;
    caption += `🧬 ${genres_names}\n`;
    caption += `⭐ ${job.vote_average || 'Sem Nota'}\t📅 ${year || 'Sem Data'}\n\n`;
    caption += `> ${job.overview}`;

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: {
          image: { url: poster_url },
          caption: caption,
          viewOnce: !data.text.match(/show/),
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
