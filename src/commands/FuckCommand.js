import { NSFW } from "nsfwhub";
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class FuckCommand {

    static identifier = "^\\s*\\,\\s*fuck\\s*(?:\\@\\d+\\s*)$";

    static async run(data) {
        console.log('FUCK COMMAND');

        const chat = await data.getChat();
        if (!chat.isGroup) {
            chat.sendMessage(
                `Burro burro! Você só pode fuder com alguém do grupo em um! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const sender_phone = data.author.replace('@c.us', '');
        const mentioned_phone = data.mentionedIds[0].replace('@c.us', '');

        const nsfw = new NSFW();
        const porn = await nsfw.fetch("fuck");
        console.log('fuck', porn);
        try {
            chat.sendMessage(
                await MessageMedia.fromUrl(porn.image.url),
                {
                    sendSeen: true,
                    isViewOnce: true,
                    quotedMessageId: data.id._serialized,
                    mentions: [data.author, data.mentionedIds[0]],
                    caption: ` @${sender_phone} está fudendo @${mentioned_phone} 😩`
                }
            );
        } catch (error) {
            console.error('ERROR FUCK COMMAND', error);
        }
    }
}