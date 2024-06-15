import Resenhazord2 from '../models/Resenhazord2.js';
import puppeteer from 'puppeteer';

export default class Rule34Command {

    static identifier = "^\\s*\\,\\s*rule34\\s*$";

    static async run(data) {

        (async () => {
            const browser = await puppeteer.launch({headless: true});
            const page = await browser.newPage();
            await page.goto(`https://rule34.xxx/index.php?page=post&s=random`);
            let rule34;
            try {
                rule34 = await page.evaluate(() => {
                    const nodeList = document.querySelectorAll('div.flexi img');
                    const imgArray = [...nodeList];

                    return imgArray.map( ({src}) => ({ src }));
                });
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {
                        viewOnce: true,
                        image: { url: rule34[0]['src'] },
                        caption: 'Aqui está a imagem que você pediu 🤗'
                    },
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
            catch (error) {
                Resenhazord2.bugsnag.notify(`RULE34 COMMAND ERROR\n${error}`);
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: 'Não consegui encontrar nada para você 😔'},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
            await browser.close();
        })();
    }
}