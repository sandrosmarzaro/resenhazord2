import type { WAMessage } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class ReactMessage {
  static async run(data: WAMessage): Promise<void> {
    await Resenhazord2.socket!.sendMessage(data.key.remoteJid!, {
      react: {
        text: '👍',
        key: data.key,
      },
    });
  }
}
