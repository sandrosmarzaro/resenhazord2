import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class MyAnimeListCommand {

    static identifier = "^\\s*\\,\\s*mal\\s*$";

    static async run(data) {

        const url = 'https://api.jikan.moe/v4/random/anime';
        axios.get(url)
            .then(response => {
                const anime = response.data;
                const image = anime.data.images.webp.large_image_url;
                const genres = anime.data.genres.map(genre => genre.name).join(', ');
                const themes = anime.data.themes.map(theme => theme.name).join(', ');
                const studios = anime.data.studios.map(studio => studio.name).join(', ');

                let caption = '';
                caption += `${anime.data.title}\n`;
                caption += `🎥 EPs: ${anime.data.episodes || 'Não sei'}\t📅 ${anime.data.year || 'Não sei'}\n`;
                caption += `⭐️ Nota: ${anime.data.score || 'Não tem'}\t🏆 Rank: #${anime.data.rank || 'Não tem'}\n`;
                caption += `🧬 Gêneros: ${genres || 'Nenhum'}\n`;
                caption += `📚 Temas: ${themes || 'Nenhum'}\n`;
                caption += `⛩ Estúdios: ${studios || 'Desconhecido'}`;

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    { image: { url: image }, caption: caption, viewOnce: true },
                    { quoted: data, ephemeralExpiration: data.expiration }
                );
            })
            .catch(error => {
                Resenhazord2.bugsnag.notify(`MYANIMELIST COMMAND ERROR\n${error}`);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    { text: `Viiixxiii... Não consegui encontrar seu anime! 🥺👉👈` },
                    { quoted: data, ephemeralExpiration: data.expiration }
                );
            });
    }
}