import { socket } from '../models/Resenhazord2.js';

export default class OiCommand {

    static identifier = "^\\s*\\,\\s*oi\\s*$";

    static async run(data) {
        console.log('OI COMMAND');


        const { message } = data.messages.pop;
        const { text } = message.extendedTextMessage;
        const sender_phone = data.author.replace('@s.whatsapp.net', '');

        try {
            socket.sendMessage(
                {
                    text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
                    sendSeen: true,
                    quotedMessageId: data.id._serialized,
                    mentions: [data.author]
                },
                {
                    quoted: message
                }
            );
        } catch (error) {
            console.error('ERROR OI COMMAND', error);
        }
    }
}