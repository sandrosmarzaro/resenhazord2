import { useMultiFileAuthState } from '@whiskeysockets/baileys'
import path from 'path'

export class CreateAuthState {

    private static session: any = path.resolve(__dirname, './session')

    public static async getAuthState() {
        return await useMultiFileAuthState(CreateAuthState.session)
    }
}