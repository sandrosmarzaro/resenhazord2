import CreateClient from '../infra/CreateClient.js';
import CreateQRCode from '../infra/CreateQRCode.js';
import MessageEvent from '../events/MessageEvent.js';

export default class Resenhazord2 {

    static client = null;

    static async connectToWhatsApp() {
        this.client = await CreateClient.getClient();
    }

    static async handlerEvents() {
        this.client.initialize();
        this.client.on('qr', qr => CreateQRCode.run(qr));
        this.client.on('authenticated', session => console.log('AUTHENTICATED', session));
        this.client.on('auth_failure', message => console.log('AUTH FAILURE', message));
        this.client.on('loading_screen', (percent, message) => console.log('LOADING SCREEN', percent, message));
        this.client.on('ready', () => console.log('CLIENT IS READY'));
        this.client.on('message_create', message => MessageEvent.run(message));
        this.client.on('disconnected', reason => console.log('CLIENT DISCONNECTED', reason));
    }
}