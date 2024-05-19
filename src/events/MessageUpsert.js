export default class MessageUpsert {
    constructor() {}

    static async run(messages, type) {
        console.log(JSON.stringify(messages, null, 2));
    }
}