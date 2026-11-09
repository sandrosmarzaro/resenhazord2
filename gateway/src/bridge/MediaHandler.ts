import type { WAMessage } from '@whiskeysockets/baileys';
import { downloadMediaMessage, generateWAMessageFromContent } from '@whiskeysockets/baileys';
import pino from 'pino';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import type { CommandData } from '../types/command.js';

export interface MediaInfo {
  type: 'image' | 'video' | 'audio' | 'sticker';
  source: 'direct' | 'quoted';
  isAnimated?: boolean;
  caption?: string;
}

type AnyMsg = Record<string, Record<string, unknown> | undefined>;

const MEDIA_TYPES = ['imageMessage', 'videoMessage', 'audioMessage', 'stickerMessage'] as const;

const TYPE_MAP: Record<string, MediaInfo['type']> = {
  imageMessage: 'image',
  videoMessage: 'video',
  audioMessage: 'audio',
  stickerMessage: 'sticker',
};

const DOWNLOAD_TIMEOUT_MS = 50_000;

export default class MediaHandler {
  // A file sent as a document still names its media family in the mimetype.
  private static readonly DOCUMENT_FAMILIES: Record<string, MediaInfo['type']> = {
    image: 'image',
    video: 'video',
    audio: 'audio',
  };

  constructor(private readonly whatsapp: WhatsAppPort) {}

  static hasDirectMedia(message: WAMessage['message']): boolean {
    const msg = message as AnyMsg | null | undefined;
    if (!msg) return false;
    return MEDIA_TYPES.some((type) => msg[type]);
  }

  detectMedia(data: CommandData): MediaInfo | null {
    const msg = data.message as AnyMsg | undefined;
    if (!msg) return null;

    return this.findDirectMedia(msg) ?? this.findQuotedMedia(msg);
  }

  private findDirectMedia(msg: AnyMsg): MediaInfo | null {
    for (const type of MEDIA_TYPES) {
      if (msg[type]) return { type: TYPE_MAP[type], source: 'direct' };
    }
    return null;
  }

  private findQuotedMedia(msg: AnyMsg): MediaInfo | null {
    const quoted = (msg.extendedTextMessage?.contextInfo as AnyMsg | undefined)?.quotedMessage as
      | AnyMsg
      | undefined;
    if (!quoted) return null;

    const sticker = quoted.stickerMessage;
    if (sticker) {
      return {
        type: 'sticker',
        source: 'quoted',
        isAnimated: (sticker.isAnimated as boolean | undefined) ?? false,
      };
    }

    return this.findQuotedDirectMedia(quoted) ?? this.findQuotedDocument(quoted);
  }

  private findQuotedDocument(quoted: AnyMsg): MediaInfo | null {
    const captioned = quoted.documentWithCaptionMessage?.message as AnyMsg | undefined;
    const document = quoted.documentMessage ?? captioned?.documentMessage;
    if (!document) return null;
    const type = MediaHandler.DOCUMENT_FAMILIES[String(document.mimetype).split('/')[0]];
    if (!type) return null;
    return {
      type,
      source: 'quoted',
      caption: typeof document.caption === 'string' ? document.caption : undefined,
    };
  }

  private findQuotedDirectMedia(quoted: AnyMsg): MediaInfo | null {
    for (const type of MEDIA_TYPES) {
      const media = quoted[type];
      if (media) {
        return {
          type: TYPE_MAP[type],
          source: 'quoted',
          caption: typeof media.caption === 'string' ? media.caption : undefined,
        };
      }
    }
    return null;
  }

  async downloadMedia(stored: WAMessage, source: string): Promise<Buffer> {
    let message: WAMessage;

    if (source === 'direct') {
      message = stored;
    } else {
      const quoted = stored.message?.extendedTextMessage?.contextInfo?.quotedMessage;
      if (!quoted) throw new Error('No quoted message found');

      message = generateWAMessageFromContent(stored.key.remoteJid!, quoted, {
        userJid: stored.key.remoteJid?.includes('@g.us')
          ? stored.key.participant!
          : stored.key.remoteJid!,
      });
    }

    const download = downloadMediaMessage(
      message,
      'buffer',
      {},
      {
        reuploadRequest: this.whatsapp.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );

    const timeout = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('Media download timed out')), DOWNLOAD_TIMEOUT_MS),
    );

    return await Promise.race([download, timeout]);
  }
}
