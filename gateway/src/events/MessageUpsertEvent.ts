import type { BaileysEventMap, WAMessage } from '@whiskeysockets/baileys';
import CommandHandler from '../handlers/CommandHandler.js';
import logger from '../infra/Logger.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class MessageUpsertEvent {
  private static readonly STATUS_JID = 'status@broadcast';

  static async run(data: BaileysEventMap['messages.upsert']): Promise<void> {
    const [message] = data.messages;
    if (data.type === 'notify') {
      MessageUpsertEvent.markRead(data.messages);
    }
    if (process.env.DEBUG === 'true' && data.type !== 'notify') {
      return;
    }
    await CommandHandler.run(message);
  }

  // A bot on a regular account otherwise leaves every chat unread. Fire-and-forget:
  // a lost receipt must never delay or fail the command.
  private static markRead(messages: WAMessage[]): void {
    const keys = messages
      .map((message) => message.key)
      .filter((key) => !key.fromMe && key.remoteJid !== MessageUpsertEvent.STATUS_JID);
    if (keys.length === 0) return;
    Resenhazord2.adapter!.readMessages(keys).catch((error: unknown) => {
      logger.warn({ event: 'read_receipt_failed', error: String(error) });
    });
  }
}
