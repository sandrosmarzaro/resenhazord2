import Resenhazord2 from "../models/Resenhazord2.js";
import { Client } from "porn-x";
import { NSFW } from "nsfwhub";

export default class PornoCommand {

    static identifier = "^\\s*\\,\\s*porno\\s*(?:ia)?\\s*$";

    static async run(data) {
        console.log('PORNO COMMAND');

        const rest_command = data.message.extendedTextMessage.text.replace(/\n*\s*\,\s*porn.\s*/, '');
        const args_command = rest_command.replace(/\s|\n/, '');
        if (args_command) {
            this.ia_porn(data)
        }
        else {
            this.real_porn(data)
        }
    }

    static async ia_porn(data) {
        const nsfw = new NSFW();
        const tags = [
            "ass", "sixtynine", "pussy", "dick", "anal", "boobs", "bdsm", "black", "easter", "bottomless",
            "blowjub", "collared", "cum", "cumsluts", "dp", "dom", "extreme", "feet", "finger", "fuck", "futa",
            "gay", "gif", "group", "hentai", "kiss", "lesbian", "lick", "pegged", "phgif", "puffies", "real",
            "suck", "tattoo", "tiny", "toys", "xmas"
        ];
        const tag = tags[Math.floor(Math.random() * tags.length)];
        const porn = await nsfw.fetch(tag);
        console.log('porno', porn);
        try {
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    video: {url: porn.image.url},
                    caption: 'Aqui está seu vídeo 🤤'
                },
                {quoted: data}
            );
        }
        catch (error) {
            console.error(`PORN COMMAND ERROR: ${error}`);
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'},
                {quoted: data}
            );
        }
    }

    static async real_porn(data) {
        const client = new Client();

        const videos = await client.getShortVideos("random");
        const video = videos[Math.floor(Math.random() * videos.length)];
        console.log('porno', video);
        try {
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    video: {url: video},
                    caption: 'Aqui está seu vídeo 🤤'
                },
                {quoted: data}
            );
        }
        catch (error) {
            console.error(`PORN COMMAND ERROR: ${error}`);
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'},
                {quoted: data}
            );
        }
    }
}