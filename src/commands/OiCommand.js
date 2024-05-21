import Resenhazord2 from '../models/Resenhazord2.js';

export default class OiCommand {
    constructor() {}

    static async run(data) {
        console.log('OiCommand.run');

        const sender_id = data.key.participant;
        const sender_phone = sender_id.split('@')[0];

        Resenhazord2.sock.sendMessage(
            data.key.remoteJid,
            {
                text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
                mentions: [sender_id]
            },
            { quoted: data }
        );
    }
}