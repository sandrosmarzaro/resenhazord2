import { isBoom } from '@hapi/boom';
import { DisconnectReason } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class ConnectionUpdateEvent {

    static async run(update) {
        const { connection, lastDisconnect, qr } = update;

        // if (qr) {
        //     console.log(`qrcode: ${qr}`);
        // }
        if (connection === 'open' && !Resenhazord2.socket.authState.creds.registered) {
            try {
                const { RESENHA_ID } = process.env;
                const RESENHA_NUMBER = RESENHA_ID.replace('@s.whatsapp.net', '');
                const pair_code = await Resenhazord2.socket.requestPairingCode(RESENHA_NUMBER);
                console.log(`Pair Code: ${pair_code}`);
            } catch (error) {
                console.error('Failed to request pairing code:', error);
            }
        }

        if (connection === 'close') {
            let shouldReconnect = false;
            if (isBoom(lastDisconnect.error)) {
                const { statusCode } = lastDisconnect.error.output;
                if (statusCode!== DisconnectReason.loggedOut) {
                    shouldReconnect = true;
                }
            }
            console.log(`Connection closed due to:`, lastDisconnect.error);
            console.log(`Attempting reconnection: ${shouldReconnect}`);
            if (shouldReconnect) {
                await Resenhazord2.connectToWhatsApp();
                Resenhazord2.handlerEvents();
            }
        }
        else if (connection === 'open') {
            console.log('opened connection');
        }
    }
}