import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type BrokerPort from '../ports/BrokerPort.js';
import type MediaHandler from './MediaHandler.js';
import type { MediaInfo } from './MediaHandler.js';
import logger from '../infra/Logger.js';

interface ConversationMentionShape {
  conversationMessage?: { contextInfo?: { mentionedJid?: string[] } };
}

export default class CommandPublisher {
  private static readonly QUEUE = 'commands';

  constructor(
    private readonly broker: BrokerPort,
    private readonly mediaHandler: MediaHandler,
  ) {}

  async publish(data: CommandData): Promise<string> {
    const id = crypto.randomUUID();
    const mediaInfo = this.mediaHandler.detectMedia(data);
    const mediaBuffer = mediaInfo ? await this.download(data, mediaInfo) : null;
    const envelope = { id, data: this.buildData(data, mediaInfo, mediaBuffer) };
    await this.broker.publish(CommandPublisher.QUEUE, Buffer.from(JSON.stringify(envelope)));
    return id;
  }

  private buildData(
    data: CommandData,
    mediaInfo: MediaInfo | null,
    mediaBuffer: Buffer | null,
  ): Record<string, unknown> {
    return {
      text: data.text,
      jid: data.key.remoteJid!,
      sender_jid: (data.key.participant ?? data.key.remoteJid)!,
      participant: data.key.participant ?? null,
      is_group: data.key.remoteJid?.includes('g.us') ?? false,
      expiration: data.expiration ?? null,
      mentioned_jids: this.mentionedJids(data),
      quoted_message_id: data.message?.extendedTextMessage?.contextInfo?.stanzaId ?? null,
      quoted_text: this.quotedText(data),
      message_id: data.key.id ?? null,
      push_name: data.pushName ?? null,
      media_type: mediaInfo?.type ?? null,
      media_source: mediaInfo?.source ?? null,
      media_is_animated: mediaInfo?.isAnimated ?? false,
      media_caption: mediaInfo?.caption ?? null,
      ...(mediaBuffer ? { media_buffer_b64: mediaBuffer.toString('base64') } : {}),
    };
  }

  private mentionedJids(data: CommandData): string[] {
    return (
      data.message?.extendedTextMessage?.contextInfo?.mentionedJid ??
      (data.message as ConversationMentionShape | null | undefined)?.conversationMessage
        ?.contextInfo?.mentionedJid ??
      []
    );
  }

  private quotedText(data: CommandData): string | null {
    const quoted = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
    if (!quoted) return null;
    return quoted.conversation ?? quoted.extendedTextMessage?.text ?? null;
  }

  private async download(data: CommandData, mediaInfo: MediaInfo): Promise<Buffer | null> {
    try {
      return await this.mediaHandler.downloadMedia(data as WAMessage, mediaInfo.source);
    } catch (error) {
      logger.warn({
        event: 'media_download_failed',
        jid: data.key.remoteJid,
        error: String(error),
      });
      return null;
    }
  }
}
