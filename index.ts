import { CreateAuthState } from './src/auth/CreateAuthState'
import { CreateSock } from './src/infra/CreateSock'
import { ConnectionUpdate } from './src/events/ConnectionUpdate'
import { MessageUpsert } from './src/events/MessageUpsert';

async function connectToWhatsApp () {

    const { state, saveCreds } = await CreateAuthState.getAuthState()
    const sock = await CreateSock.getSock(state);

    sock.ev.on('connection.update', update => ConnectionUpdate.run(update))
    sock.ev.on('messages.upsert', message => MessageUpsert.run(message))
    sock.ev.on('connection.update', saveCreds)
}

connectToWhatsApp()
