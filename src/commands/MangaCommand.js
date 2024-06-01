import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;
import request_pkg from 'request';
const request = request_pkg;

export default class MangaCommand {

    static identifier = "^\\s*\\,\\s*manga\\s*$";

    static async run(data) {

        const chat = await data.getChat();
        const base_url = 'https://api.jikan.moe/v4/random/manga';

        request(base_url, async (error, response, body) => {

            if (error) {
                console.error('MANGA COMMAND ERROR', error);
                chat.sendMessage(
                    `Viiixxiii... Não consegui encontrar seu manga! 🥺👉👈`,
                    { sendSeen: true, quotedMessageId: data.id._serialized }
                );
                return;
            }

            const manga = JSON.parse(body);
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
            chat.sendMessage(
                await MessageMedia.fromUrl(image),
                {
                    sendSeen: true,
                    caption: caption,
                    isViewOnce: true,
                    quotedMessageId: data.id._serialized
                }
            );
        });
    }
}