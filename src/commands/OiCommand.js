export default class OiCommand {

    static async run(data) {
        console.log('OI COMMAND');

        const chat = await data.getChat();
        const sender_phone = data.author.replace('@c.us', '');
        
        try {
            chat.sendMessage(
                `Vai se fuder @${sender_phone} filho da puta! 🖕`,
                {
                    sendSeen: true,
                    quotedMessageId: data.id._serialized,
                    mentions: [data.author]
                }
            );
        } catch (error) {
            console.error('ERROR OI COMMAND', error);
        }
    }
}