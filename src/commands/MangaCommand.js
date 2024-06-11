import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class MangaCommand {

    static identifier = "^\\s*\\,\\s*manga\\s*$";

    static async run(data) {
        console.log('MANGA COMMAND');

        const base_url = 'https://api.jikan.moe/v4/random/manga';
        axios.get(base_url)
            .then(response => {
                const manga = response.data;
                const image = manga.data.images.webp.large_image_url;
                const genres = manga.data.genres.map(genre => genre.name).join(', ');
                const themes = manga.data.themes.map(theme => theme.name).join(', ');
                const authors = manga.data.authors.map(author => author.name).join(', ');

                let caption = '';
                caption += `${manga.data.title}\n`;
                caption += `🎥 Capítulos: ${manga.data.chapters || 'Não sei'}\t📅 ${manga.data.year || 'Não sei'}\n`
                caption += `⭐️ Nota: ${manga.data.score || 'Não tem'}\t🏆 Rank: #${manga.data.rank || 'Não tem'}\n`;
                caption += `🧬 Gêneros: ${genres || 'Nenhum'}\n`;
                caption += `📚 Temas: ${themes || 'Nenhum'}\n`;
                caption += `🖋 Autores: ${authors || 'Desconhecido'}`;

                console.log('manga', manga);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {image: {url: image}, caption: caption, viewOnce: true},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            })
            .catch(error => {
                console.error('MANGA COMMAND ERROR', error);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Viiixxiii... Não consegui encontrar seu manga! 🥺👉👈`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            });
    }
}