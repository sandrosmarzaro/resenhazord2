import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;
import request_pkg from 'request';
const request = request_pkg;

export default class AnimeCommand {

    static identifier = "^\\s*\\,\\s*anime\\s*(?:nsfw|sfw)?\\s*$";

    static async run(data) {
        console.log('ANIME COMMAND');

        const chat = await data.getChat();

        const sfw_tags = [
            'waifu', 'neko', 'shinobu', 'megumin', 'bully', 'cuddle', 'cry', 'hug', 'awoo', 'kiss', 'lick',
            'pat', 'smug', 'bonk', 'yeet', 'blush', 'smile', 'wave', 'highfive', 'handhold', 'nom', 'bite',
            'glomp', 'slap', 'kill', 'kick', 'happy', 'wink', 'poke', 'dance', 'cringe'
        ];
        const nsfw_tags = ['waifu', 'neko', 'trap', 'blowjob'];

        const rest_command = data.body.replace(/^\s*\,\s*anime\s*/, '');
        const is_nsfw = rest_command.match(/nsfw/);

        let tag;
        is_nsfw ? tag = nsfw_tags[Math.floor(Math.random() * nsfw_tags.length)] : tag = sfw_tags[Math.floor(Math.random() * sfw_tags.length)];
        let type;
        is_nsfw ? type = 'nsfw' : type = 'sfw';

        const url = `https://api.waifu.pics/${type}/${tag}`;
        try {
            request(url, async (error, response, body) => {
                const anime = JSON.parse(body);
                console.log('anime', anime);

                if (error) {
                    console.error('POKEMON COMMAND ERROR', error);
                    return;
                }

                chat.sendMessage(
                    await MessageMedia.fromUrl(anime.url),
                    {
                        sendSeen: true,
                        isViewOnce: true,
                        quotedMessageId: data.id._serialized,
                        caption: `Aqui está uma foto de anime para você! 😊`
                    }
                );
            });
        } catch (error) {
            console.error('ERROR ANIME COMMAND', error);

            chat.sendMessage(
                'Viiixxiii... Não consegui baixar a foto! 🥺👉👈',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
    }
}