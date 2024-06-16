import Resenhazord2 from "../models/Resenhazord2.js";
import { PornHub } from "pornhub.js";

export default class PornhubCommand {

    static identifier = "^\\s*\\,\\s*pornhub\\s*$";

    static async run(data) {

        const pornhub = new PornHub();

        let video;
        let has_240p = false;
        let tries = 0;
        do {
            video = await pornhub.randomVideo();
            Resenhazord2.bugsnag.notify(`VIDEO\n${JSON.stringify(video)}`);
            video.mediaDefinitions.forEach(media => {
                if (typeof media.quality === 'number') {
                    has_240p = media.quality === 240;
                }
                else {
                    has_240p = media.quality.includes(240);
                }
            });

            if (!has_240p) {
                tries++;
            }
            if (tries > 500) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }
        } while (!has_240p);

        const caption = `🔞 *${video.title || 'Aqui está seu vídeo 🤤'}* 🔞`;
        const url = video.mediaDefinitions.find(media => media.quality === 240 || media.quality.includes(240)).videoUrl;

        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            { text: video},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {
                viewOnce: true,
                caption: caption,
                video: { url: url }
            },
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }
}