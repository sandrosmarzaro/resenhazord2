import { DisconnectReason } from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'

export class ConnectionUpdate {
    public static async run(update: any) {
        const { connection, lastDisconnect } = update

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error as Boom)?.output?.statusCode !== DisconnectReason.loggedOut
            console.log('connection closed due to ', lastDisconnect.error, ', reconnecting ', shouldReconnect)

            if (shouldReconnect) {
                // TODO: reconnect
            }
        }
        else if (connection === 'open') {
            console.log('opened connection')
        }
    }
}