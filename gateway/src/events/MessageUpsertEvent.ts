import type { BaileysEventMap } from '@whiskeysockets/baileys';
import CommandHandler from '../handlers/CommandHandler.js';

export default class MessageUpsertEvent {
  static async run(data: BaileysEventMap['messages.upsert']): Promise<void> {
    const [message] = data.messages;
    if (process.env.DEBUG === 'true' && data.type !== 'notify') {
      return;
    }
    await CommandHandler.run(message);
  }
}
