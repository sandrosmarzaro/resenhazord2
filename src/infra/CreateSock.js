import { makeWASocket } from "@whiskeysockets/baileys"

export default class CreateSock {
    constructor() {}

    static config = {
        printQRInTerminal: true,
        syncFullHistory: false,
        version: [2, 2413, 1]
    };

    static async getSock(state) {
        return makeWASocket({ auth: state,...CreateSock.config });
    }
}
