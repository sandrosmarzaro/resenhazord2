import Resenhazord2 from '../models/Resenhazord2.js';
import axios from 'axios';
import * as cheerio from 'cheerio';

export default class Rule34Command {
    static identifier = "^\\s*\\,\\s*rule34\\s*$";

    static async run(data) {
        const TIMEOUT = 30000;

        try {
            const response = await axios.get('https://rule34.xxx/index.php?page=post&s=random', {
                timeout: TIMEOUT,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                }
            });

            const $ = cheerio.load(response.data);
            const images = [];

            $('div.flexi img').each((i, elem) => {
                const src = $(elem).attr('src');
                if (src) {
                    images.push({ src });
                }
            });

            if (images.length === 0) {
                throw new Error('Nenhuma imagem encontrada');
            }

            const banner_url = 'https://kanako.store/products/futa-body';
            const url = images[0]['src'] === banner_url && images.length > 1
                ? images[1]['src']
                : images[0]['src'];

            if (!url) {
                throw new Error('URL da imagem inválida');
            }

            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    image: { url: url },
                    caption: 'Aqui está a imagem que você pediu 🤗'
                },
                { quoted: data, ephemeralExpiration: data.expiration }
            );
        }
        catch (error) {
            console.log(`RULE34 COMMAND ERROR\n${error}`);

            let errorMessage = 'Não consegui encontrar nada para você 😔';

            if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
                errorMessage = 'Tempo limite excedido ao tentar acessar o site 😔';
            }
            else if (error.response?.status) {
                errorMessage = `Erro ao acessar o site (${error.response.status}) 😔`;
            }

            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: errorMessage },
                { quoted: data, ephemeralExpiration: data.expiration }
            );
        }
    }
}