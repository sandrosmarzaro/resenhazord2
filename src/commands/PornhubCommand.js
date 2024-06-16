import Resenhazord2 from "../models/Resenhazord2.js";
import { PornHub } from "pornhub.js";

export default class PornhubCommand {

    static identifier = "^\\s*\\,\\s*pornhub\\s*$";

    static async run(data) {

        const pornhub = new PornHub();

        let video;
        let has_240p = false;
        let tries = 0;
        let url;
        do {
            video = await pornhub.randomVideo();
            video.mediaDefinitions.forEach(media => {
                if (typeof media.quality === 'number' && media.quality === 240) {
                    has_240p = media.quality === 240;
                    url = media.videoUrl;
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