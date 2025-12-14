import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class YugiohCommand {

    static identifier = "^\\s*\\,\\s*ygo\\s*(?:show)?\\s*(?:dm)?$";

    static async run(data) {

        const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
        axios.get(url)
            .then(async response => {
                const card = response.data["data"][0];
                const card_image = card.card_images[0].image_url;
                card.desc = card.desc.replace(/\n/g, '');

                const chat_id = data.key.remoteJid
                const DM_FLAG_ACTIVE = data.text.match(/dm/)
                if (DM_FLAG_ACTIVE && data.key.participantAlt) {
                    chat_id = data.key.participantAlt
                }
                await Resenhazord2.socket.sendMessage(
                    chat_id,
                    {
                        viewOnce: !(data.text.match(/show/)),
                        image: {url: card_image},
                        caption: `*${card.name}*\n\n> ${card.desc}`
                    },
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            })
            .catch(async error => {
                console.log(`YUGIOH COMMAND ERROR\n${error}`);
                await Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text:'Viiixxiii... Não consegui baixar a carta! 🥺👉👈'},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            });
    }
}