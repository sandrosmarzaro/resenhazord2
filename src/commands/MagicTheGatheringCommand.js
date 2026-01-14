import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';

export default class Heartstone {

    static identifier = "^\\s*\\,\\s*mtg\\s*(?:show)?\\s*(?:dm)?$";

    static async run(data) {
        const API_URL = 'https://api.magicthegathering.io/v1/cards';
        const PAGE_SIZE = 100;
        try {
            const initial_response = await axios.get(`${API_URL}?pageSize=${PAGE_SIZE}`);

            const total_cards = parseInt(initial_response.headers['total-count']);
            const total_tages = Math.ceil(total_cards / PAGE_SIZE);

            const random_page = Math.floor(Math.random() * total_tages) + 1;

            const page_response = await axios.get(`${API_URL}?pageSize=${PAGE_SIZE}&page=${random_page}`);
            const cards_on_page = page_response.data.cards;

            const card = cards_on_page[Math.floor(Math.random() * cards_on_page.length)];
            const caption = `*${card.name}*\n\n> ${card.text}`

            let chat_id = data.key.remoteJid
            const DM_FLAG_ACTIVE = data.text.match(/dm/)
            if (DM_FLAG_ACTIVE && data.key.participant) {
                chat_id = data.key.participant
            }
            await Resenhazord2.socket.sendMessage(
                chat_id,
                {image: {url: card.imageUrl	}, caption: caption, viewOnce: !(data.text.match(/show/))},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`MAGICTHEGATHERING COMMAND ERROR\n${error}`);
            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Viiixxiii... Não consegui baixar a carta! 🥺👉👈`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}