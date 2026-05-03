import type { WAMessage } from '@whiskeysockets/baileys';
import logger from '../infra/Logger.js';

interface ConversationMentionShape {
  conversationMessage?: { contextInfo?: { mentionedJid?: string[] } };
}

export default class BotMentionDetector {
  private static readonly RESENHA_JID = process.env.RESENHA_JID ?? '';
  private static readonly RESENHAZORD2_JID = process.env.RESENHAZORD2_JID ?? '';
  private static readonly RESENHAZORD2_LID = process.env.RESENHAZORD2_LID ?? '';

  private static readonly BOT_NUMERIC_IDS: readonly string[] = [
    BotMentionDetector.RESENHAZORD2_JID.split('@')[0],
    BotMentionDetector.RESENHA_JID.split('@')[0],
    BotMentionDetector.RESENHAZORD2_LID,
  ].filter((id): id is string => Boolean(id));

  static mentionsBot(data: WAMessage, text: string): boolean {
    if (!text) return false;
    const textLower = text.toLowerCase();
    const mentionedJids = BotMentionDetector.collectMentionedJids(data);

    const hasJidMention = mentionedJids.some(BotMentionDetector.isBotId);
    const hasTextMention = BotMentionDetector.BOT_NUMERIC_IDS.some((botId) =>
      textLower.includes(botId.toLowerCase()),
    );

    logger.debug({
      event: 'mention_check',
      mentionedJids,
      hasJidMention,
      hasTextMention,
      text: textLower,
    });

    return hasJidMention || hasTextMention;
  }

  private static isBotId(id?: string): boolean {
    if (!id) return false;
    const numericPart = id.split('@')[0];
    return BotMentionDetector.BOT_NUMERIC_IDS.includes(numericPart);
  }

  private static collectMentionedJids(data: WAMessage): string[] {
    return (
      data.message?.extendedTextMessage?.contextInfo?.mentionedJid ??
      (data.message as ConversationMentionShape | null | undefined)?.conversationMessage
        ?.contextInfo?.mentionedJid ??
      []
    );
  }
}
