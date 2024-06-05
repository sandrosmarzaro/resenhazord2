import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {

    static async run(data) {
        console.log('MESSAGE EVENT');
        console.log(JSON.stringify(data, null, 2));

        const [message] = data.messages;
        // if (!message.fromMe) {
        //     console.log(JSON.stringify(message.body, null, 2));
        // }

        const { RESENHA_ID, RESENHA_TEST_ID } = process.env;
        const chat = message.key.remoteJid;
        if (!chat.includes(RESENHA_ID) && !chat.includes(RESENHA_TEST_ID)) {
            return;
        }

        CommandHandler.run(message);
    }
}