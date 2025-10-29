import Resenhazord2 from "../models/Resenhazord2.js";
import { NSFW } from "nsfwhub";

export default class FuckCommand {

    static identifier = "^\\s*\\,\\s*fuck\\s*(?:\\@\\d+\\s*)$";

    static async run(data) {

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode fuder com alguém do grupo em um! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const sender_phone = data.key.remoteJidAlt.replace('@lid', '');
        const mentioned_phone = data.message.extendedTextMessage.contextInfo.mentionedJid[0].replace('@lid', '');

        const nsfw = new NSFW();
        const porn = await nsfw.fetch("fuck");
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    video: {url: porn.image.url},
                    mentions: [data.key.remoteJidAlt, data.message.extendedTextMessage.contextInfo.mentionedJid[0]],
                    caption: `@${sender_phone} está fudendo @${mentioned_phone} 😩`
                },
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        } catch (error) {
            console.log(`ERROR FUCK COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui foder @${sender_phone} 😔`, mentions: [data.key.remoteJidAlt]},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}