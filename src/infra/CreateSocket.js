import { makeWASocket } from "@whiskeysockets/baileys";
import pino from "pino";

export default class CreateSocket {

    static config = {
        qrTimeout: 0,
        printQRInTerminal: false,
        syncFullHistory: false,
        logger: pino({
            transport: {
                target: 'pino-pretty',
                options: {
                    colorize: true,
                    colorizeObjects: true
                }
            }
        }),
        generateHighQualityLinkPreview: true
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
