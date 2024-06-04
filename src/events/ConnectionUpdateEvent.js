import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';

export default class ConnectionUpdateEvent {

    static async run(update) {
        const { connection, lastDisconnect } = update;

        if (connection === 'close') {
            let shouldReconnect = false;
            if (isBoom(lastDisconnect.error)) {
                const {statusCode} = lastDisconnect.error.output;
                if (statusCode!== DisconnectReason.loggedOut) {
                    shouldReconnect = true;
                }
            }
            console.log('connection closed due to ', lastDisconnect.error, ', reconnecting ', shouldReconnect);

            if (shouldReconnect) {
                // TODO: reconnect
            }
        }
        else if (connection === 'open') {
            console.log('opened connection');
        }
    }
}