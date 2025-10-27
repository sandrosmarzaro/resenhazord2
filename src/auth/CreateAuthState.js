import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { useMultiFileAuthState } from '@whiskeysockets/baileys';
import { mkdir } from 'fs/promises';

export default class CreateAuthState {

    static async getAuthState() {
        const dir_name = dirname(fileURLToPath(import.meta.url));
        const session_path = join(process.cwd(), 'auth_session');

        try {
            await mkdir(session_path, { recursive: true });
            return await useMultiFileAuthState(session_path);
        } catch (error) {
            console.error('Failed to create/load auth state:', error);
            throw error;
        }
    }
}