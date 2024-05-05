import { Browsers, makeWASocket } from "@whiskeysockets/baileys"

export class CreateSock {

    private static config = {
        printQRInTerminal: true,
        browser: Browsers.windows(""),
        syncFullHistory: true
    }

    public static async getSock(state: any) {
        return makeWASocket({ auth: state, ...CreateSock.config })
    }
}