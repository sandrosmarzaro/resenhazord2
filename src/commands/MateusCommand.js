export default class MateusCommand {

    static async run(data) {
        console.log('MATEUS COMMAND');

        const chat = await data.getChat();
        const probability = (Math.random() * 101).toFixed(2).replace('.', ',');

        try {
            chat.sendMessage(
                `A probabilidade de Mateus nascer agora é de ${probability} % 🧐`,
                {
                    sendSeen: true,
                    quotedMessageId: data.id._serialized
                }
            );
        } catch (error) {
            console.error('ERROR MATEUS COMMAND', error);
        }
    }
}