export default class AllCommand {
    static async run(data) {
        console.log('ALL COMMAND');

        const chat = await data.getChat(data);
        if (!chat.isGroup) {
            chat.sendMessage(
                `Burro burro! Você só pode marcar o grupo em um grupo! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const participants = await chat.participants;
        const text_inserted = data.body.replace(/\n*\s*\,\s*all\s*/, '');
        let message = text_inserted.length > 0 ? text_inserted : '';
        message += '\n\n';
        for (const participant of participants) {
            message += `@${participant.id.user} `;
        }
        const participants_ids = participants.map(participant => participant.id._serialized);
        chat.sendMessage(
            message,
            { sendSeen: true, mentions: participants_ids}
        );
    }
}