import Resenhazord2 from "../models/Resenhazord2.js";

export default class OiCommand {

    static identifier = "^\\s*\\,\\s*oi\\s*$";

    static async run(data) {

        const sender = data.key.participant ? data.key.participant : data.key.remoteJidAlt
        const sender_phone = sender.replace(/@lid/, '');
        try {
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
                    mentions: [sender]
                },
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        } catch (error) {
            console.log(`ERROR OI COMMAND\n${error}`);
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui responder @${sender_phone} 😔`, mentions: [sender]},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}