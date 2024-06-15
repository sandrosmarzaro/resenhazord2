import CreateSocket from '../infra/CreateSocket.js';
import CreateAuthState from '../auth/CreateAuthState.js';
import MessageUpsertEvent from '../events/MessageUpsertEvent.js';
import ConnectionUpdate from '../events/ConnectionUpdateEvent.js';

export default class Resenhazord2 {

    static auth_state = null;
    static socket = null;
    static bugsnag = null;

    static async connectToWhatsApp() {
        this.auth_state = await CreateAuthState.getAuthState();
        this.socket = await CreateSocket.getSocket(this.auth_state.state);
    }

    static async handlerEvents() {
        this.socket.ev.on('connection.update', update => ConnectionUpdate.run(update));
        this.socket.ev.on('messages.upsert', data => MessageUpsertEvent.run(data));
        await this.socket.ev.on('creds.update', this.auth_state.saveCreds);
    }
}