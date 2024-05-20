import CreateAuthState from '../auth/CreateAuthState.js';
import CreateSock from '../infra/CreateSock.js';
import ConnectionUpdate from '../events/ConnectionUpdate.js';
import MessageUpsert from '../events/MessageUpsert.js';

export default class Resenhazord2 {
    constructor() {}

    static sock = null;
    static authState = null;

    static async connectToWhatsApp() {
        Resenhazord2.authState = await CreateAuthState.getAuthState();
        Resenhazord2.sock = await CreateSock.getSock(Resenhazord2.authState.state);
    }

    static async handlerEvents() {
        Resenhazord2.sock.ev.on('connection.update', (update) => ConnectionUpdate.run(update));
        Resenhazord2.sock.ev.on('messages.upsert', ({ messages, type }) => MessageUpsert.run(messages, type));
        Resenhazord2.sock.ev.on('connection.update', Resenhazord2.authState.saveCreds);
    }
}