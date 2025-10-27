import { Browsers, makeWASocket } from "@whiskeysockets/baileys";
import pino from "pino";

export default class CreateSocket {

    static config = {
        qrTimeout: 300000,
        browser: Browsers.baileys('Resenhazord2'),
        printQRInTerminal: false,
        syncFullHistory: false,
        logger: pino({
            transport: {
                target: 'pino-pretty',
                options: {
                    colorize: true,
                    colorizeObjects: true
                }
            },
            level: 'error'
        }),
        generateHighQualityLinkPreview: true,
        retryRequestDelayMs: 2000,
        connectTimeoutMs: 60000,
        defaultQueryTimeoutMs: 60000,
        emitOwnEvents: true
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
