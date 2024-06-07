import Resenhazord2 from '../models/Resenhazord2.js';
import pkg from 'nayan-media-downloader';
const { alldown } = pkg;

export default class MediaCommand {

    static identifier = "^\\s*\\,\\s*media\\s*";

    static async run(data) {
        console.log('MEDIA COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        let url = data.message.extendedTextMessage.text.replace(/\n*\s*\,\s*media\s*/, '');
        if (url.length === 0) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: 'Me passa o link do vídeo que você quer baixar 🤗' },
                { quoted: data, ephemeralExpiration: exp }
            );
            return;
        }
        url = url.replace('x.com', 'twitter.com');
        url = url.replace('instagram.com/reel/', 'instagram.com/p/');
        url = url.replace(/\/\?.*$/, '/');

        const response = await alldown(url);
        console.log('url', url);
        console.log('media', response);
        if (!response.status) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈` },
                { quoted: data, ephemeralExpiration: exp }
            );
            return;
        }
        let link;
        if (response.data.high && response.data.high.startsWith('http')) {
            link = response.data.high;
        }
        else {
            link = response.data.low;
        }


        let title;
        if (response.data.title === 'undefined💔') {
            title = 'Enfia seu video no cu! 🤬';
        }
        else {
            title = response.data.title;
        }

        await Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {
                viewOnce: true,
                video: { url: link },
                caption: title
            },
            { quoted: data, ephemeralExpiration: exp }
        );
    }
}