import pkg from 'nayan-media-downloader';
const { twitterdown } = pkg;
import wa_pkg from 'whatsapp-web.js';
const { MessageMedia } = wa_pkg;

export default class TwitterCommand {
    static async run(data) {
        console.log('TWITTER COMMAND');

        const chat = await data.getChat();
        let url = data.body.replace(/\n*\s*\,\s*x\s*/, '');

        if (url.length === 0) {
            chat.sendMessage(
                `Burro burro! Você não enviou um link de tweet! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }
        if (!/https:\/\/(?:twitter|x)\.com\/.*\/status\/\d+/.test(url)) {
            chat.sendMessage(
                `Burro burro! Você tem enviar um link do Twitter! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }
        url = url.replace('x.com', 'twitter.com');

        const response = await twitterdown(url);
        console.log(response);
        if (!response.status) {
            chat.sendMessage(
                `Viiixxiii... Não consegui baixar o vídeo! 🥺👉👈`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }
        let link = response.data.SD;
        if (response.data.HD) {
            response.data.link = response.data.HD;
        }

        await chat.sendMessage(
            await MessageMedia.fromUrl(link),
            {
                sendSeen: true,
                quotedMessageId: data.id._serialized,
                caption: 'Aqui está o seu vídeo do 🐦'
            }
        );
    }
}