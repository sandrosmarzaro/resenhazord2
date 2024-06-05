import { makeWASocket } from "@whiskeysockets/baileys";

export default class CreateSocket {

    static config = {
        printQRInTerminal: true
    };

    static async getSocket(state) {
        return makeWASocket({ auth: state, ...this.config });
    }
}
