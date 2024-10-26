import Resenhazord2 from '../models/Resenhazord2.js';
import puppeteer from 'puppeteer';

export default class Rule34Command {
    static identifier = "^\\s*\\,\\s*rule34\\s*$";

    static async run(data) {
        const TIMEOUT = 60000;
        const NAVIGATION_TIMEOUT = 30000;

        try {
            const browser = await puppeteer.launch({
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
                timeout: TIMEOUT
            });
            const page = await browser.newPage();

            page.setDefaultNavigationTimeout(NAVIGATION_TIMEOUT);
            page.setDefaultTimeout(TIMEOUT);

            await page.goto(`https://rule34.xxx/index.php?page=post&s=random`, {
                waitUntil: 'networkidle0',
                timeout: NAVIGATION_TIMEOUT
            });

            const rule34 = await page.evaluate(() => {
                const nodeList = document.querySelectorAll('div.flexi img');
                const imgArray = [...nodeList];
                return imgArray.map(({ src }) => ({ src }));
            });

            const banner_url = 'https://kanako.store/products/futa-body';
            const url = rule34[0]['src'] === banner_url ? rule34[1]['src'] : rule34[0]['src'];

            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {
                    viewOnce: true,
                    image: { url: url },
                    caption: 'Aqui está a imagem que você pediu 🤗'
                },
                { quoted: data, ephemeralExpiration: data.expiration }
            );

            await browser.close();
        }
        catch (error) {
            console.log(`RULE34 COMMAND ERROR\n${error}`);

            const errorMessage = error instanceof puppeteer.errors.TimeoutError
                ? 'Tempo limite excedido ao tentar acessar o site 😔'
                : 'Não consegui encontrar nada para você 😔';

            await Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                { text: errorMessage },
                { quoted: data, ephemeralExpiration: data.expiration }
            );

            if (browser) {
                await browser.close();
            }
        }
    }
}