import puppeteer from 'puppeteer';
import pkg from 'whatsapp-web.js';
const { MessageMedia } = pkg;

export default class Rule34Command {

    static identifier = "^\\s*\\,\\s*rule34\\s*$";

    static async run(data) {
        console.log('RULE34 COMMAND');

        const chat = await data.getChat();
        (async () => {
            const browser = await puppeteer.launch({headless: true});
            const page = await browser.newPage();
            await page.goto(`https://rule34.xxx/index.php?page=post&s=random`);

            const rule34 = await page.evaluate(() => {
                const nodeList = document.querySelectorAll('div.flexi img');
                const imgArray = [...nodeList];

                return imgArray.map( ({src}) => ({ src }));
            });
            await browser.close();
            console.log('rule34', rule34[0]['src']);
            await chat.sendMessage(
                await MessageMedia.fromUrl(rule34[0]['src']),
                {
                    sendSeen: true,
                    isViewOnce: true,
                    quotedMessageId: data.id._serialized,
                    caption: 'Aqui está a imagem que você pediu 🤗'
                }
            );
        })();
    }
}