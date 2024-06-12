import Resenhazord2 from "../models/Resenhazord2.js";

export default class AllCommand {

    static identifier = "^\\s*\\,\\s*all\\s*";

    static async run(data) {
        console.log('ALL COMMAND');

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode marcar o grupo em um grupo! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const { participants } = await Resenhazord2.socket.groupMetadata(data.key.remoteJid);
        const text_inserted = data.text.replace(/\n*\s*\,\s*all\s*/, '');
        let message = text_inserted.length > 0 ? text_inserted : '';
        message += '\n\n';
        for (const participant of participants) {
            message += `@${participant.id.replace('@s.whatsapp.net', '')} `;
        }
        const participants_ids = participants.map(participant => participant.id);
        Resenhazord2.socket.sendMessage(
            data.key.remoteJid,
            {text: message, mentions: participants_ids},
            {quoted: data, ephemeralExpiration: data.expiration}
        );
    }
}