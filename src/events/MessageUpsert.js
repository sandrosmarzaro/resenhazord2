import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsert {
    constructor() {}

    static async run(messages, type) {
        console.log('MessageUpsert.run');
        console.log('type:', type);
        console.log(JSON.stringify(messages, null, 2));

        const {RESENHA_ID, RESENHA_TEST_ID} = process.env;
        const chat = messages[0].key.remoteJid;
        if (!chat.includes(RESENHA_ID) && !chat.includes(RESENHA_TEST_ID)) {
            return;
        }

        CommandHandler.run(messages[0]);
    }
}