import Resenhazord2 from "../models/Resenhazord2.js";

export default class OiCommand {

    static identifier = "^\\s*\\,\\s*oi\\s*$";

    static async run(data) {

        const sender_phone = data.key.remoteJidAlt.replace('@lid', '');
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
                    mentions: [data.key.remoteJidAlt]
                },
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        } catch (error) {
            console.log(`ERROR OI COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui responder @${sender_phone} 😔`, mentions: [data.key.remoteJidAlt]},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}