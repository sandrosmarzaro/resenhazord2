import { makeWASocket } from "@whiskeysockets/baileys";

export default class CreateSocket {

    static config = {
        printQRInTerminal: true,
        syncFullHistory: false
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
