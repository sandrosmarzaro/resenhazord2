import Resenhazord2 from '../models/Resenhazord2.js';

export default class MateusCommand {
    constructor() {}

    static async run(data) {
        console.log('MateusCommand.run');

        const sender_id = data.key.participant;
        const probability = (Math.random() * 101).toFixed(2).replace('.', ',');

        Resenhazord2.sock.sendMessage(
            data.key.remoteJid,
            {
                text: `A probabilidade de Mateus nascer é de ${probability} %`,
                mentions: [sender_id]
            },
            { quoted: data }
        );
    }
}