import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class FilmeSerieCommand {

    static identifier = "^\\s*\\,\\s*(?:filme|s.rie)\\s*(?:top|pop)?\\s*$";

    static async run(data) {
        console.log('FILME SERIE COMMAND');

        const rest_command = data.text.replace(/\s*\,(?:filme|serie)\s*\s*/i, '').replace(/\s|\n/, '');
        const mode = rest_command.match(/top/i) ? 'top_rated' : 'popular';
        const type = data.message.extendedTextMessage.text.match(/filme/i) ? 'movie' : 'tv';
        const url = `https://api.themoviedb.org/3/${type}/${mode}`;

        const page = Math.floor(Math.random() * 25) + 1;
        try {
            const response = await axios.get(url, {
                params: {
                    api_key: process.env.TMDB_API_KEY,
                    language: 'pt-BR',
                    page: page
                }
            });
            const jobs = response.data.results;
            const job = jobs[Math.floor(Math.random() * jobs.length)];
            const poster_url = `https://image.tmdb.org/t/p/w500${job.poster_path}`
            console.log('filme serie', poster_url);

            const genres_url = `https://api.themoviedb.org/3/genre/${type}/list`
            const genres_response = await axios.get(genres_url, {
                params: {
                    api_key: process.env.TMDB_API_KEY,
                    language: 'pt-BR'
                }
            });
            const { genres } = genres_response.data;
            const genres_names = job.genre_ids.map(id => genres.find(genre => genre.id === id).name).join(', ');

            const year = type === 'movie' ? job.release_date.slice(0, 4) : job.first_air_date.slice(0, 4);
            const name = type === 'movie' ? job.title : job.name;

            let caption = '';
            caption += `*${name}*\n\n`;
            caption += `🧬 ${genres_names}\n`;
            caption += `⭐ ${job.vote_average || 'Sem Nota'}\t📅 ${year || 'Sem Data'}\n\n`;
            caption += `> ${job.overview}`;

            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { image: { url: poster_url }, caption: caption, viewOnce: true },
                { quoted: data, ephemeralExpiration: data.expiration }
            );
        }
        catch (error) {
            console.error('ERROR FILME SERIE COMMAND', error);
            const message = type === 'movie' ? 'seu filminho' : 'sua seriezinha';
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: `Viiixxiii... Não consegui buscar ${message}! 🥺👉👈`},
                { quoted: data, ephemeralExpiration: data.expiration }
            );
        }
    }
}