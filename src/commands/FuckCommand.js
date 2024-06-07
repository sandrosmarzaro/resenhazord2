import Resenhazord2 from "../models/Resenhazord2.js";
import { NSFW } from "nsfwhub";

export default class FuckCommand {

    static identifier = "^\\s*\\,\\s*fuck\\s*(?:\\@\\d+\\s*)$";

    static async run(data) {
        console.log('FUCK COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode fuder com alguém do grupo em um! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: exp}
            );
            return;
        }

        const sender_phone = data.key.participant.replace('@s.whatsapp.net', '');
        const mentioned_phone = data.message.extendedTextMessage.contextInfo.mentionedJid[0].replace('@s.whatsapp.net', '');

        const nsfw = new NSFW();
        const porn = await nsfw.fetch("fuck");
        console.log('fuck', porn);
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    video: {url: porn.image.url},
                    mentions: [data.key.participant, data.message.extendedTextMessage.contextInfo.mentionedJid[0]],
                    caption: `@${sender_phone} está fudendo @${mentioned_phone} 😩`
                },
                {quoted: data, ephemeralExpiration: exp}
            );
        } catch (error) {
            console.error('ERROR FUCK COMMAND', error);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui foder @${sender_phone} 😔`, mentions: [data.key.participant]},
                {quoted: data, ephemeralExpiration: exp}
            );
        }
    }
}