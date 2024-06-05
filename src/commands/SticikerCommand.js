import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;

export default class StickerCommand {
    static identifier = "^\\s*\\,\\s*stic\\s*$";

    static async run(message) {
        console.log('STICKER COMMAND');

        if (!message.hasMedia) {
            chat.sendMessage(
                'Burro burro! Você precisa enviar uma imagem ou gif para fazer um sticker! 🤦‍♂️',
                { sendSeen: true, quotedMessageId: message.id._serialized }
            );
            return;
        }

        const chat = await message.getChat();
        let media = await message.downloadMedia();
        console.log('media', media);
        if (message._data.isGif) {
            media.mimetype = 'image/gif';
        }
        try {
            chat.sendMessage(
                media,
                {
                    sendSeen: true,
                    sendMediaAsSticker: true,
                    stickerAuthor: 'Resenhazord2 - Bot',
                    quotedMessageId: message.id._serialized
                }
            );
        } catch (error) {
            console.error('ERROR STICKER COMMAND', error);
        }
    }
}