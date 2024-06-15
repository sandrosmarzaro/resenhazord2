import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {

    static async run(data) {
        const [message] = data.messages;
        const { RESENHA_ID, RESENHA_TEST_ID } = process.env;
        const chat = message.key.remoteJid;
        if (!chat.includes(RESENHA_ID) && !chat.includes(RESENHA_TEST_ID)) {
            return;
        }

        CommandHandler.run(message);
    }
}