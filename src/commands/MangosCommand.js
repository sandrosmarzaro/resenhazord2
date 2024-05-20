import Resenhazord2 from '../models/Resenhazord2.js';

export default class MangosCommand {
    constructor() {}

    static async run(data) {
        console.log('MangosCommand.run');

        const probability = Math.floor(Math.random() * 101).toFixed(2).replace('.', ',');

        Resenhazord2.sock.sendMessage(
            data.key.remoteJid,
            {
                text: `A probabilidade de Mangos II nascer é de ${probability}%`,
                mentions: [sender_id]
            },
            { quoted: data }
        );
    }
}