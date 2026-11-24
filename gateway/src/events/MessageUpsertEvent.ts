import {
  normalizeMessageContent,
  type BaileysEventMap,
  type WAMessage,
} from '@whiskeysockets/baileys';
import { stickerAudioStore } from '../cache/index.js';
import CommandHandler from '../handlers/CommandHandler.js';
import logger from '../infra/Logger.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class MessageUpsertEvent {
  private static readonly STATUS_JID = 'status@broadcast';
  private static readonly mutedChats = new Set<string>();

  static async run(data: BaileysEventMap['messages.upsert']): Promise<void> {
    const messages = data.messages.filter((message) => !MessageUpsertEvent.isGroupStatus(message));
    const [message] = messages;
    if (!message) return;
    MessageUpsertEvent.keepStickerAudio(messages);
    if (data.type === 'notify') {
      MessageUpsertEvent.markRead(messages);
      MessageUpsertEvent.muteNewChats(messages);
    }
    if (process.env.DEBUG === 'true' && data.type !== 'notify') {
      return;
    }
    await CommandHandler.run(message);
  }

  // Members' group statuses stay invisible to the bot: reading one would list the bot
  // among its viewers, and a caption is not a command.
  private static isGroupStatus(message: WAMessage): boolean {
    return !!(message.message?.groupStatusMessage || message.message?.groupStatusMessageV2);
  }

  // A reply quotes an audio sticker without its audio, so keep it for the lookup.
  // Fire-and-forget like the receipts: Redis must never delay the command.
  private static keepStickerAudio(messages: WAMessage[]): void {
    for (const message of messages) {
      const audio = normalizeMessageContent(message.message)?.stickerMessage?.audioMessage;
      if (!audio) continue;
      stickerAudioStore.save(message.key, audio).catch((error: unknown) => {
        logger.warn({ event: 'sticker_audio_save_failed', error: String(error) });
      });
    }
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
