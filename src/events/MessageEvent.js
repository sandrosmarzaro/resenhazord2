import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageEvent {

    static async run(message) {
        console.log('MESSAGE EVENT');
        if (!message.fromMe) {
            console.log(JSON.stringify(message, null, 2));
        }

        const {RESENHA_ID, RESENHA_TEST_ID} = process.env;
        const chat = message.id.remote;
        if (!chat.includes(RESENHA_ID) && !chat.includes(RESENHA_TEST_ID)) {
            return;
        }

        CommandHandler.run(message);
    }
}