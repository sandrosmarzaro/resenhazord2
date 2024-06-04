import { makeWASocket } from "@whiskeysockets/baileys";

export default class CreateSocket {

    static config = {
        printQRInTerminal: true,
        version: [2, 2413, 1]
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
