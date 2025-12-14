import Resenhazord2 from '../models/Resenhazord2.js';

export default class MediaCommand {

    static identifier = "^\\s*\\,\\s*media\\s*";

    static async run(data) {

        let url = data.text.replace(/\n*\s*\,\s*media\s*/, '');
        if (url.length === 0) {
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: 'Me passa o link do vídeo que você quer baixar 🤗' },
                { quoted: data, ephemeralExpiration: data.expiration }
            );
            return;
        }
        url = url.replace('x.com', 'twitter.com');
        url = url.replace('instagram.com/reel/', 'instagram.com/p/');
        url = url.replace(/\/\?.*$/, '/');

        await Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            { text: `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈` },
            { quoted: data, ephemeralExpiration: data.expiration }
        );
    }
}