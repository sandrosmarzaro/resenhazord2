import CreateSocket from '../infra/CreateSocket.js';
import CreateAuthState from '../auth/CreateAuthState.js';
import MessageUpsertEvent from '../events/MessageUpsertEvent.js';
import ConnectionUpdate from '../events/ConnectionUpdateEvent.js';

export default class Resenhazord2 {

    static auth_state = null;
    static socket = null;
    static isConnecting = false;

    static async connectToWhatsApp() {
        if (this.isConnecting) {
            console.log('Connection already in progress...');
            return;
        }
        this.isConnecting = true;
        try {
            this.auth_state = await CreateAuthState.getAuthState();
            this.socket = await CreateSocket.getSocket(this.auth_state.state);
            console.log('Socket created successfully');
        } catch (error) {
            console.error('Failed to connect:', error.message);
            throw error;
        } finally {
            this.isConnecting = false;
        }
    }

    static async handlerEvents() {
        if (!this.socket) {
            console.error('Cannot setup handlers: socket is null');
            return;
        }
        this.socket.ev.removeAllListeners('connection.update');

        this.socket.ev.on('connection.update', async (update) => { await ConnectionUpdate.run(update) });
        this.socket.ev.on('messages.upsert', async (data) => { await MessageUpsertEvent.run(data) });
        await this.socket.ev.on('creds.update', this.auth_state.saveCreds);
    }

    static async cleanup() {
        if (this.socket) {
            console.log('Cleaning up existing socket...');

            try {
                this.socket.ev.removeAllListeners();
                await this.socket.end();
            } catch (error) {
                console.error('Error during cleanup:', error.message);
            }
            this.socket = null;
        }
        this.isConnecting = false;
    }
}