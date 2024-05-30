import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;
import request_pkg from 'request';
const request = request_pkg;

export default class YugiohCommand {

    static identifier = "^\\s*\\,\\s*ygo\\s*$";

    static async run(data) {

        const chat = await data.getChat();
        const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
        try {
            request(url, async (error, response, body) => {
                const card = JSON.parse(body);
                const card_image = card.card_images[0].image_url;
                console.log('yugioh', card_image);

                if (error) {
                    console.error('YUGIOH COMMAND ERROR', error);
                    return;
                }

                chat.sendMessage(
                    await MessageMedia.fromUrl(card_image),
                    {
                        sendSeen: true,
                        quotedMessageId: data.id._serialized,
                        caption: `${card.name}\n\n${card.desc}`
                    }
                );
            });
        } catch (error) {
            console.error('ERROR ANIME COMMAND', error);

            chat.sendMessage(
                'Viiixxiii... Não consegui baixar a carta! 🥺👉👈',
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
    }
}