import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class ConnectionUpdateEvent {

    static async run(update) {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            Resenhazord2.bugsnag.notify(`qrcode: ${qr}`);
        }

        if (connection === 'close') {
            let shouldReconnect = false;
            if (isBoom(lastDisconnect.error)) {
                const { statusCode } = lastDisconnect.error.output;
                if (statusCode!== DisconnectReason.loggedOut) {
                    shouldReconnect = true;
                }
            }
            Resenhazord2.bugsnag.notify(`connection closed due to ${lastDisconnect.error}`);
            Resenhazord2.bugsnag.notify(`reconnecting ${shouldReconnect}`)
            if (shouldReconnect) {
                await Resenhazord2.connectToWhatsApp();
                Resenhazord2.handlerEvents();
            }
        }
        else if (connection === 'open') {
            Resenhazord2.bugsnag.notify('opened connection');
        }
    }
}