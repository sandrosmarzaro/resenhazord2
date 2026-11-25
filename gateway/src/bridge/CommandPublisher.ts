import type { WAMessage, WAMessageKey } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type BrokerPort from '../ports/BrokerPort.js';
import type MediaHandler from './MediaHandler.js';
import type { MediaInfo } from './MediaHandler.js';
import type StickerAudioStore from '../cache/StickerAudioStore.js';
import logger from '../infra/Logger.js';
import { injectPublishTrace } from '../infra/Otel.js';

interface ConversationMentionShape {
  conversationMessage?: { contextInfo?: { mentionedJid?: string[] } };
}

export default class CommandPublisher {
  private static readonly QUEUE = 'commands';
  // A real sticker's audio is ~0.5 MB (60s of opus); the cap keeps a forged one from
  // doubling the envelope's memory next to the 64 MiB media download.
  private static readonly MAX_STICKER_AUDIO_BYTES = 4 * 1024 * 1024;

  constructor(
    private readonly broker: BrokerPort,
    private readonly mediaHandler: MediaHandler,
    private readonly stickerAudio: StickerAudioStore,
  ) {}

  async publish(data: CommandData): Promise<string> {
    const id = crypto.randomUUID();
    const mediaInfo = this.mediaHandler.detectMedia(data);
    const mediaBuffer = mediaInfo ? await this.download(data as WAMessage, mediaInfo.source) : null;
    const audioBuffer =
      mediaInfo?.type === 'sticker' ? await this.downloadStickerAudio(data) : null;
    const envelope: Record<string, unknown> = {
      id,
      data: {
        ...this.buildData(data, mediaInfo, mediaBuffer),
        ...(audioBuffer ? { media_audio_b64: audioBuffer.toString('base64') } : {}),
      },
    };
    // Open the trace here and carry it in the envelope so the core bot's command
    // handling hangs under this gateway span (edge -> core).
    injectPublishTrace(envelope);
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
      sender_jid: this.senderJid(data.key),
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

  private senderJid(key: WAMessageKey): string {
    // Lid-addressed groups put the LID in `participant`; the phone-number JID we
    // store and mention lives in `participantAlt`. Prefer the PN so sender matching
    // survives WhatsApp's lid migration.
    if (key.addressingMode === 'lid' && key.participantAlt) {
      return key.participantAlt;
    }
    // `||`, not `??`: template DMs arrive with participant set to an empty string.
    return (key.participant || key.remoteJid)!;
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

  // The quoted copy of an audio sticker carries no audio: find it by the quoted id.
  private async downloadStickerAudio(data: CommandData): Promise<Buffer | null> {
    const contextInfo = data.message?.extendedTextMessage?.contextInfo;
    const jid = data.key.remoteJid!;
    if (!contextInfo?.stanzaId) return null;
    const audioMessage = await this.stickerAudio.find(jid, contextInfo.stanzaId);
    if (!audioMessage) return null;
    const key = { remoteJid: jid, id: contextInfo.stanzaId, participant: contextInfo.participant };
    return this.download(
      { key, message: { audioMessage } },
      'direct',
      CommandPublisher.MAX_STICKER_AUDIO_BYTES,
    );
  }

  private async download(
    message: WAMessage,
    source: string,
    maxBytes?: number,
  ): Promise<Buffer | null> {
    try {
      return await this.mediaHandler.downloadMedia(message, source, maxBytes);
    } catch (error) {
      logger.warn({
        event: 'media_download_failed',
        jid: message.key.remoteJid,
        error: String(error),
      });
      return null;
    }
  }
}
