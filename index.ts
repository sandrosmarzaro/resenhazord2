import { CreateAuthState } from './src/auth/CreateAuthState'
import { CreateSock } from './src/infra/CreateSock'
import { ConnectionUpdate } from './src/events/ConnectionUpdate'
import { MessageUpsert } from './src/events/MessageUpsert';

async function connectToWhatsApp () {

    const { state, saveCreds } = await CreateAuthState.getAuthState()
    const sock = await CreateSock.getSock(state);

    sock.ev.on('connection.update', ConnectionUpdate.run)
    sock.ev.on('messages.upsert', MessageUpsert.run)
    sock.ev.on('connection.update', saveCreds)
}

connectToWhatsApp()
