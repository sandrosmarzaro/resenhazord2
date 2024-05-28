export default class D20Command {

    static async run (data) {
        console.log('D20 COMMAND');
        const chat = await data.getChat();

        const d20 = Math.floor(Math.random() * 20) + 1;
        await chat.sendMessage(
            `Aqui está sua rolada: ${d20} 🎲`,
            { sendSeen: true, quotedMessageId: data.id._serialized }
        );
    }
}