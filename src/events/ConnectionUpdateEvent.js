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
            let reconnectDelay = 5000;

            if (lastDisconnect?.error) {
                if (isBoom(lastDisconnect.error)) {
                    const { statusCode } = lastDisconnect.error.output;
                    shouldReconnect = statusCode !== DisconnectReason.loggedOut;

                    if (statusCode === 428) {
                        reconnectDelay = 10000;
                    }
                } else {
                    shouldReconnect = true;
                }

                console.log('Connection closed due to:', {
                    error: lastDisconnect.error.message || lastDisconnect.error,
                    statusCode: lastDisconnect.error.output?.statusCode,
                    shouldReconnect,
                    reconnectDelay
                });
            }

            if (shouldReconnect) {
                console.log(`Attempting reconnection in ${reconnectDelay/1000} seconds...`);
                setTimeout(async () => {
                    try {
                        await Resenhazord2.connectToWhatsApp();
                        await Resenhazord2.handlerEvents();
                    } catch (error) {
                        console.error('Reconnection failed:', error);
                    }
                }, reconnectDelay);
            }
        }
        else if (connection === 'open') {
            console.log('opened connection');
        }
    }
}