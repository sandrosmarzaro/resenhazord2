import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class FilmeSerieCommand {
  static identifier = '^\\s*\\,\\s*(?:filme|s.rie)\\s*(?:top|pop)?\\s*(?:show)?\\s*(?:dm)?$';

  static async run(data) {
    const type = data.text.match(/filme/i) ? 'movie' : 'tv';
    const rest_command = data.text.replace(/\s*,(?:filme|serie)\s*\s*/i, '').replace(/\s|\n/, '');
    const mode = rest_command.match(/top/i) ? 'top_rated' : 'popular';
    const url = `https://api.themoviedb.org/3/${type}/${mode}`;

    const page = Math.floor(Math.random() * 25) + 1;
    try {
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
        .map((id) => genres.find((genre) => genre.id === id).name)
        .join(', ');

      const year = type === 'movie' ? job.release_date.slice(0, 4) : job.first_air_date.slice(0, 4);
      const name = type === 'movie' ? job.title : job.name;

      let caption = '';
      caption += `*${name}*\n\n`;
      caption += `🧬 ${genres_names}\n`;
      caption += `⭐ ${job.vote_average || 'Sem Nota'}\t📅 ${year || 'Sem Data'}\n\n`;
      caption += `> ${job.overview}`;

      let chat_id = data.key.remoteJid;
      const DM_FLAG_ACTIVE = data.text.match(/dm/);
      if (DM_FLAG_ACTIVE && data.key.participant) {
        chat_id = data.key.participant;
      }
      await Resenhazord2.socket.sendMessage(
        chat_id,
        { image: { url: poster_url }, caption: caption, viewOnce: !data.text.match(/show/) },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR FILME SERIE COMMAND\n${error}`);
      const message = type === 'movie' ? 'seu filminho' : 'sua seriezinha';
      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        { text: `Viiixxiii... Não consegui buscar ${message}! 🥺👉👈` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
