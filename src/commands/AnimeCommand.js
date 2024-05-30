import { NekosAPI } from "nekosapi";
import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;

export default class AnimeCommand {

    static identifier = "^\\s*\\,\\s*anime\\s*$";

    static async run(data) {
        console.log('ANIME COMMAND');

        const chat = await data.getChat();
        const nekos = new NekosAPI();

        try {
            const image = await nekos.getRandomImage();
            console.log('anime', image.image_url);
            chat.sendMessage(
                await MessageMedia.fromUrl(image.image_url),
                {
                    sendSeen: true,
                    isViewOnce: true,
                    quotedMessageId: data.id._serialized,
                    caption: `Aqui está uma foto no estilo de anime para você! 😊`
                }
            );
        } catch (error) {
            console.error('ERROR ANIME COMMAND', error);
        }
    }
}