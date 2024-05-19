import CreateAuthState from './src/auth/CreateAuthState.js';
import CreateSock from './src/infra/CreateSock.js';
import ConnectionUpdate from './src/events/ConnectionUpdate.js';
import MessageUpsert from './src/events/MessageUpsert.js';

async function connectToWhatsApp() {
    const authState = await CreateAuthState.getAuthState();
    const sock = await CreateSock.getSock(authState.state);

    sock.ev.on('connection.update', (update) => ConnectionUpdate.run(update));
    sock.ev.on('messages.upsert', ({ messages, type }) => MessageUpsert.run(messages, type));
    sock.ev.on('connection.update', authState.saveCreds);
}

connectToWhatsApp();
