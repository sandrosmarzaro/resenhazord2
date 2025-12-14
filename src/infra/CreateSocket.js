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
        };

        return makeWASocket(config);
    }
}