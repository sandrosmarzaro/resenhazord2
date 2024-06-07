import Resenhazord2 from "../models/Resenhazord2.js";

export default class MateusCommand {

    static identifier = "^\\s*\\,\\s*mateus\\s*$";

    static async run(data) {
        console.log('MATEUS COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const probability = (Math.random() * 101).toFixed(2).replace('.', ',');
        try {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `A probabilidade de Mateus nascer agora é de ${probability} % 🧐`},
                {quoted: data, ephemeralExpiration: exp}
            );
        } catch (error) {
            console.error('ERROR MATEUS COMMAND', error);
        }
    }
}