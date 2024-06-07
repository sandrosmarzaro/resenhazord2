import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class YugiohCommand {

    static identifier = "^\\s*\\,\\s*ygo\\s*$";

    static async run(data) {
        console.log('YUGIOH COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const url = 'https://db.ygoprodeck.com/api/v7/randomcard.php';
        axios.get(url)
            .then(response => {
                const card = response.data;
                const card_image = card.card_images[0].image_url;
                console.log('yugioh', card_image);

                card.desc = card.desc.replace(/\n/g, '\n> ');

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {
                        viewOnce: true,
                        image: {url: card_image},
                        caption: `*${card.name}*\n\n> ${card.desc}`
                    },
                    {quoted: data, ephemeralExpiration: exp}
                );
            })
            .catch(error => {
                console.error('YUGIOH COMMAND ERROR', error);

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text:'Viiixxiii... Não consegui baixar a carta! 🥺👉👈'},
                    {quoted: data, ephemeralExpiration: exp}
                );
            });
    }
}