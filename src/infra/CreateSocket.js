import { makeWASocket } from "@whiskeysockets/baileys";
import pino from "pino";

export default class CreateSocket {

    static config = {
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
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
