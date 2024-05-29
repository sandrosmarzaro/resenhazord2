import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;

export default class CreateClient {

    static async getClient() {
        const auth_path ='./src/auth/session';

        const EXECUTABLE_PATHS = {
            linux: '/usr/bin/google-chrome-stable',
            darwin: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            win32: 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe'
        };
        const executablePath = EXECUTABLE_PATHS[process.platform];

        return new Client({
            puppeteer: {
                executablePath: executablePath
            },
            webVersionCache: {
                remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2413.51-beta.html',
                type: 'remote'
            },
            authStrategy: new LocalAuth({
                dataPath: auth_path
            })
        });
    }
}
