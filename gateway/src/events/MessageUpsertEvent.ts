import type { BaileysEventMap, WAMessage } from '@whiskeysockets/baileys';
import CommandHandler from '../handlers/CommandHandler.js';
import logger from '../infra/Logger.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class MessageUpsertEvent {
  private static readonly STATUS_JID = 'status@broadcast';
  private static readonly mutedChats = new Set<string>();

  static async run(data: BaileysEventMap['messages.upsert']): Promise<void> {
    const [message] = data.messages;
    if (data.type === 'notify') {
      MessageUpsertEvent.markRead(data.messages);
      MessageUpsertEvent.muteNewChats(data.messages);
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

  // Keeps the bot's phone from notifying. Baileys has no 'new chat' event, so each chat
  // is muted on its first message in this process; a restart re-mutes, which is harmless.
  private static muteNewChats(messages: WAMessage[]): void {
    const jids = new Set(messages.map((message) => message.key.remoteJid));
    for (const jid of jids) {
      if (!jid || jid === MessageUpsertEvent.STATUS_JID || MessageUpsertEvent.mutedChats.has(jid))
        continue;
      MessageUpsertEvent.mutedChats.add(jid);
      Resenhazord2.adapter!.muteChat(jid).catch((error: unknown) => {
        MessageUpsertEvent.mutedChats.delete(jid);
        logger.warn({ event: 'chat_mute_failed', error: String(error) });
      });
    }
  }

  static reset(): void {
    MessageUpsertEvent.mutedChats.clear();
  }
}
