import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {

    static async run(data) {
        console.log('MESSAGE EVENT');
        console.log(JSON.stringify(data, null, 2));
        return;

        if (!message.fromMe) {
            console.log(JSON.stringify(message.body, null, 2));
        }

        const {RESENHA_ID, RESENHA_TEST_ID} = process.env;
        const chat = message.id.remote;
        if (!chat.includes(RESENHA_ID) && !chat.includes(RESENHA_TEST_ID)) {
            return;
        }

        CommandHandler.run(message);
    }
}