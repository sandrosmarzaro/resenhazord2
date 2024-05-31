import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;
import request_pkg from 'request';
const request = request_pkg;

export default class MyAnimeListCommand {

    static identifier = "^\\s*\\,\\s*mal\\s*$";

    static async run(data) {

        const chat = await data.getChat();
        const url = 'https://api.jikan.moe/v4/random/anime';

        request(url, async (error, response, body) => {

            if (error) {
                console.error('MYANIMELIST COMMAND ERROR', error);
                chat.sendMessage(
                    `Viiixxiii... Não consegui encontrar seu anime! 🥺👉👈`,
                    { sendSeen: true, quotedMessageId: data.id._serialized }
                );
                return;
            }

            const anime = JSON.parse(body);
            const image = anime.data.images.webp.large_image_url;
            const genres = anime.data.genres.map(genre => genre.name).join(', ');
            const themes = anime.data.themes.map(theme => theme.name).join(', ');
            const studios = anime.data.studios.map(studio => studio.name).join(', ');

            let caption = '';
            caption += `${anime.data.title}\n`;
            caption += `🎥 EPs: ${anime.data.episodes || 'Não sei'}\t📅 ${anime.data.year || 'Não sei'}\n`
            caption += `⭐️ Nota: ${anime.data.score || 'Não tem'}\t🏆 Rank: #${anime.data.rank || 'Não tem'}\n`;
            caption += `🧬 Gêneros: ${genres || 'Nenhum'}\n`;
            caption += `📚 Temas: ${themes || 'Nenhum'}\n`;
            caption += `⛩ Estúdios: ${studios || 'Desconhecido'}`;

            console.log('myanimelist', anime);
            chat.sendMessage(
                await MessageMedia.fromUrl(image),
                { sendSeen: true, quotedMessageId: data.id._serialized, caption: caption }
            );
        });
    }
}