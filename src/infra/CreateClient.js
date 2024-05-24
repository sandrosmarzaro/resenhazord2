import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;

export default class CreateClient {

    static auth_path = './src/auth/session';

    static async getClient() {
        return new Client({
            puppeteer: {
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
            },
            webVersionCache: {
                remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2413.51-beta.html',
                type: 'remote'
            },
            authStrategy: new LocalAuth({
                dataPath: this.auth_path
            })
        });
    }
}
