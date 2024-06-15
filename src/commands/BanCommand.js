import Resenhazord2 from "../models/Resenhazord2.js";

export default class BanCommand {

    static identifier = "^\\s*\\,\\s*ban\\s*(?:\\@\\d+\\s*)*\\s*$";

    static async run(data) {

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode remover alguém em um grupo! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const group = await Resenhazord2.socket.groupMetadata(data.key.remoteJid);
        const { participants } = group;
        const { RESENHAZORD2_ID } = process.env;
        const is_resenhazord2_admin = participants.find(
            participant => participant.id === RESENHAZORD2_ID
        ).admin;
        if (!is_resenhazord2_admin) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Vai se foder! Eu não sou admin! 🖕`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const ban_list = data.message?.extendedTextMessage?.contextInfo?.mentionedJid;
        if (!ban_list.length) {
            let is_bot = false;
            do {
                let random_participant = participants[Math.floor(Math.random() * participants.length)];
                is_bot = (random_participant.id === RESENHAZORD2_ID) || random_participant.id === group.owner;
                if (!is_bot) {
                    Resenhazord2.socket.sendMessage(
                        data.key.remoteJid,
                        {
                            text: `Se fudeu! @${random_participant.id.replace('@s.whatsapp.net', '')} 🖕`,
                            mentions: [random_participant]
                        },
                        {quoted: data, ephemeralExpiration: data.expiration}
                    ).then (async () => {
                        await Resenhazord2.socket.groupParticipantsUpdate(
                            data.key.remoteJid,
                            [random_participant.id],
                            "remove"
                        );
                    });
                }
            } while (!is_bot);
        }
        else {
            const owner_is_admin = participants.find(
                participant => participant.id === group.owner
            ).admin;
            for (const participant of ban_list) {
                if ((participant === RESENHAZORD2_ID) ||
                    (participant === group.owner ) && owner_is_admin) {
                    continue;
                }
                const participant_phone = participant.replace('@s.whatsapp.net', '');
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Se fudeu! @${participant_phone} 🖕`, mentions: [participant]},
                    {quoted: data, ephemeralExpiration: data.expiration}
                ).then (async () => {
                    await Resenhazord2.socket.groupParticipantsUpdate(
                        data.key.remoteJid,
                        [participant],
                        "remove"
                    );
                });
            }
        }
    }
}