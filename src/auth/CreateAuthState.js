import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { useMultiFileAuthState } from '@whiskeysockets/baileys';

export default class CreateAuthState {
    constructor() {}

    static async getAuthState() {
        const dir_name = dirname(fileURLToPath(import.meta.url));
        const session_path = join(dir_name, './session');

        return await useMultiFileAuthState(session_path);
    }
}