export default class BanCommand {

    static identifier = "^\\s*\\,\\s*ban\\s*(?:\\@\\d+\\s*)*\\s*$";

    static async run(data) {
        console.log('BAN COMMAND');

        const chat = await data.getChat(data);
        if (!chat.isGroup) {
            chat.sendMessage(
                `Burro burro! Você só pode remover alguém em um grupo! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const { participants } = chat;
        const { RESENHAZORD2_ID } = process.env;
        const is_resenhazord2_admin = participants.find(
            participant => participant.id._serialized === RESENHAZORD2_ID
        ).isAdmin;
        if (!is_resenhazord2_admin) {
            chat.sendMessage(
                `Vai se foder! Eu não sou admin! 🖕`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const ban_list = data.mentionedIds;
        if (ban_list.length === 0) {
            let is_bot = false;
            do {
                let random_participant = participants[Math.floor(Math.random() * participants.length)];
                is_bot = random_participant.id._serialized === RESENHAZORD2_ID;
                if (!is_bot) {
                    chat.sendMessage(
                        `Se fudeu! @${random_participant.id.user} 🖕`,
                        { sendSeen: true, quotedMessageId: data.id._serialized, mentions: [random_participant.id._serialized]}
                    ).then (async () => {
                        await chat.removeParticipants([random_participant.id._serialized]);
                    });
                }
            } while (!is_bot);
        } else {
            for (const participant of ban_list) {
                const participant_phone = participant.replace('@c.us', '');
                chat.sendMessage(
                    `Se fudeu! @${participant_phone} 🖕`,
                    { sendSeen: true, quotedMessageId: data.id._serialized, mentions: [participant]}
                ).then (async () => {
                    await chat.removeParticipants([participant]);
                });
            }
        }
    }
}