import Resenhazord2 from "../models/Resenhazord2.js";
import { PornHub } from "pornhub.js";

export default class PornhubCommand {

    static identifier = "^\\s*\\,\\s*pornhub\\s*$";

    static async run(data) {

        const random_url = 'https://pt.pornhub.com/random';
        const pornhub = new PornHub();

        let video;
        let has_240p = false;
        do {
            video = await pornhub.getVideo(random_url);
            has_240p = video.mediaDefinitions.some(media => media.quality === 240 || media.quality.includes(240));
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