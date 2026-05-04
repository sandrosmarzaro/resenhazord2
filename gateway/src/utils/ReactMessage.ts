import type { WAMessage } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class ReactMessage {
  static async run(data: WAMessage): Promise<void> {
    const adapter = Resenhazord2.adapter;
    const jid = data.key.remoteJid;
    if (!adapter || !jid) return;
    await adapter.sendMessage(jid, {
      react: {
        text: '👍',
        key: data.key,
      },
    });
  }
}
