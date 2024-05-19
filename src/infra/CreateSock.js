import { makeWASocket } from "@whiskeysockets/baileys"

export default class CreateSock {
    constructor() {}

    static config = {
        printQRInTerminal: true,
        syncFullHistory: true
    };

    static async getSock(state) {
        return makeWASocket({ auth: state,...CreateSock.config });
    }
}
