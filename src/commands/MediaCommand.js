import pkg from 'nayan-media-downloader';
const { alldown } = pkg;
import wa_pkg from 'whatsapp-web.js';
const { MessageMedia } = wa_pkg;

export default class MediaCommand {

    static identifier = "^\\s*\\,\\s*media\\s*";

    static async run(data) {
        console.log('MEDIA COMMAND');

        const chat = await data.getChat();
        let url = data.body.replace(/\n*\s*\,\s*media\s*/, '');

        if (url.length === 0) {
            chat.sendMessage(
                `Burro burro! Você não enviou um link de algum vídeo! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
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
            chat.sendMessage(
                `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
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

        await chat.sendMessage(
            await MessageMedia.fromUrl(link, { unsafeMime: true }),
            {
                sendSeen: true,
                quotedMessageId: data.id._serialized,
                caption: title
            }
        );
    }
}