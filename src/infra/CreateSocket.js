import { Browsers, makeWASocket } from "@whiskeysockets/baileys";
import pino from "pino";

export default class CreateSocket {

    static config = {
        qrTimeout: 300000,
        browser: Browsers.macOS('Chrome'),
        printQRInTerminal: true,
        syncFullHistory: false,
        logger: pino({
            transport: {
                target: 'pino-pretty',
                options: {
                    colorize: true,
                    colorizeObjects: true,
                    translateTime: true
                }
            },
            level: 'warn'
        }),
        generateHighQualityLinkPreview: true,
        retryRequestDelayMs: 2000,
        connectTimeoutMs: 60000,
        defaultQueryTimeoutMs: 60000,
        emitOwnEvents: true,
        markOnlineOnConnect: false,
        version: [2, 2323, 4],
        browser: ['Chrome', 'Desktop', '1.0.0'],
        linkPreviewImageThumbnailWidth: 192,
        transactionOpts: { maxCommits: 10, delayMs: 3000 },
        getMessage: async () => undefined
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
