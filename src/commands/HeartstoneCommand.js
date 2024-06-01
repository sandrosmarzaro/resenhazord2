import axios from 'axios';
import pkg_wa from 'whatsapp-web.js';
const { MessageMedia } = pkg_wa;

export default class Heartstone {

    static identifier = "^\\s*\\,\\s*hs\\s*$";

    static async run(data) {
        console.log('HEARTSTONE COMMAND');

        const { BNET_ID, BNET_SECRET } = process.env;
        const access_token = await this.get_access_token(BNET_ID, BNET_SECRET);
        const chat = await data.getChat();
        if (!access_token) {
            chat.sendMessage(
                `Não consegui entrar na Battle.net, manda a Blizzard tomar no cu! 🤷‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const api_url = 'https://us.api.blizzard.com/hearthstone/cards?locale=pt_BR';

        try {
            const first_response = await axios.get(api_url, {
                headers: {
                    'Authorization': `Bearer ${access_token}`
                },
                params: {
                    pageSize: 1
                }
            });
            const { pageCount } = first_response.data;
            const random_page = Math.floor(Math.random() * pageCount) + 1;

            const response = await axios.get(api_url, {
                headers: {
                    'Authorization': `Bearer ${access_token}`
                },
                params: {
                    page: random_page,
                    pageSize: 1
                }
            });

            const card = response.data.cards[0];
            console.log('hearthstone', card);
            const description = card.text.replace(/\<\/?b\>/g, '*');
            const caption = `*${card.name}*\n\n_"${card.flavorText}"_\n\n${description}`;
            chat.sendMessage(
                await MessageMedia.fromUrl(card.image),
                { sendSeen: true, quotedMessageId: data.id._serialized, caption: caption }
            );
        }
        catch (error) {
            console.error('Error fetching Hearthstone cards:', error);
            chat.sendMessage(
                `Não consegui buscar as cartas do Hearthstone, manda a Blizzard tomar no cu! 🤷‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }
    }

    static async get_access_token(bnet_id, bnet_secret) {
        const token_url = 'https://oauth.battle.net/token'
        const auth = Buffer.from(`${bnet_id}:${bnet_secret}`).toString('base64');

        try {
            const response = await axios.post(token_url, 'grant_type=client_credentials', {
                headers: {
                    'Authorization': `Basic ${auth}`,
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            return response.data.access_token;
        }
        catch (error) {
            console.error('Error fetching access token:', error);
            return null;
        }
    }
}