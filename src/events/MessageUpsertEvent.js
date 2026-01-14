import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {

    static async run(data) {
        const [message] = data.messages;
        const { RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID } = process.env;
        const chat = message.key.remoteJid;
        if (![RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID].includes(chat)) {
            return;
        }

        await CommandHandler.run(message);
    }
}