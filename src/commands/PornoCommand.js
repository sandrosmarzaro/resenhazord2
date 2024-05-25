import { Client } from "porn-x";
import { NSFW } from "nsfwhub";
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class PornoCommand {

    static async run(data) {
        console.log('PORNO COMMAND');

        const chat = await data.getChat();
        const rest_command = data.body.replace(/\n*\s*\,\s*porno\s*/, '');
        const args_command = rest_command.replace(/\s|\n/, '');
        if (args_command) {
            this.ia_porn(data, chat)
        }
        else {
            this.real_porn(data, chat)
        }
    }

    static async ia_porn(data, chat) {
        const nsfw = new NSFW();
        const tags = [
            "ass", "sixtynine", "pussy", "dick", "anal", "boobs", "bdsm", "black", "easter", "bottomless",
            "blowjub", "collared", "cum", "cumsluts", "dp", "dom", "extreme", "feet", "finger", "fuck", "futa",
            "gay", "gif", "group", "hentai", "kiss", "lesbian", "lick", "pegged", "phgif", "puffies", "real",
            "suck", "tattoo", "tiny", "toys", "xmas"
        ];
        const tag = tags[Math.floor(Math.random() * tags.length)];
        const porn = await nsfw.fetch(tag);
        console.log(porn);
        try {
            await chat.sendMessage(
                await MessageMedia.fromUrl(porn.image.url),
                {
                    sendSeen: true,
                    isViewOnce: true,
                    sendVideoAsGif: true,
                    quotedMessageId: data.id._serialized,
                    caption: 'Aqui está o porno que você pediu 🤗',
                }
            );
        }
        catch (error) {
            console.error(`PORN COMMAND ERROR: ${error}`);
        }
    }

    static async real_porn(data, chat) {
        await chat.sendMessage(
            'Burro burro! Função em manutenção 👷🏼‍♂️🏗\nao invés desse pode usar o ,porno ia 😈',
            { sendSeen: true, quotedMessageId: data.id._serialized }
        );
        return;
        const client = new Client();

        const videos = await client.getShortVideos("random");
        console.log('videos', videos);
        const video = videos[Math.floor(Math.random() * videos.length)];
        console.log('video', video);
        try {
            console.log('SENDING VIDEO');
            const message = await chat.sendMessage(
                await MessageMedia.fromUrl(video),
                {
                    sendSeen: true,
                    sendVideoAsGif: true,
                    quotedMessageId: data.id._serialized,
                    caption: 'Aqui está o vídeo que você pediu 🤗',
                }
            );
            console.log('VIDEO SENT');
            console.log('message', message);
        }
        catch (error) {
            console.error(`PORN COMMAND ERROR: ${error}`);
        }
    }
}