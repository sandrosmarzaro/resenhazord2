import { makeWASocket } from "@whiskeysockets/baileys";
import pino from "pino";

export default class CreateSocket {
    static async getSocket(state) {

        const config = {
            auth: state,
            logger: pino({
                level: 'silent'
            }),
            qrTimeout: 60000,
            syncFullHistory: false,
            markOnlineOnConnect: false,
            generateHighQualityLinkPreview: true,
            puppeteerOptions: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-background-networking'
                ]
            }
        };

        return makeWASocket(config);
    }
}