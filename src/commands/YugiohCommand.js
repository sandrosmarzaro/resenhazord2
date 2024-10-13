import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class YugiohCommand {

    static identifier = "^\\s*\\,\\s*ygo\\s*$";

    static async run(data) {

        const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
        axios.get(url)
            .then(response => {
                const card = response.data;
                const card_image = card.card_images[0].image_url;
                card.desc = card.desc.replace(/\n/g, '');

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {
                        viewOnce: true,
                        image: {url: card_image},
                        caption: `*${card.name}*\n\n> ${card.desc}`
                    },
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            })
            .catch(error => {
                console.log(`YUGIOH COMMAND ERROR\n${error}`);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text:'Viiixxiii... Não consegui baixar a carta! 🥺👉👈'},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            });
    }
}