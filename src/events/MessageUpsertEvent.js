import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {

    static async run(data) {
        const [message] = data.messages;
        const { RESENHA_ID, RESENHAZORD2_ID, RESENHA_TEST_ID } = process.env;
        const chat = message.key.remoteJid;
        if (![RESENHA_ID, RESENHAZORD2_ID, RESENHA_TEST_ID].includes(chat)) {
            return;
        }

        CommandHandler.run(message);
    }
}