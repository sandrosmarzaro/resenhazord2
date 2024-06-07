import Resenhazord2 from "../models/Resenhazord2.js";

export default class D20Command {

    static identifier = "^\\s*\\,\\s*d20\\s*$";

    static async run (data) {
        console.log('D20 COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const d20 = Math.floor(Math.random() * 20) + 1;
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Aqui está sua rolada: ${d20} 🎲`},
                {quoted: data, ephemeralExpiration: exp}
            );
        }
        catch (error) {
            console.error('ERROR D20 COMMAND', error);

            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Não consegui te dar uma rolada... 😔'},
                {quoted: data, ephemeralExpiration: exp}
            );
        }
    }
}