import type { Readable } from 'node:stream';
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
  // Any member can quote a 2 GB document: count the bytes that arrive, since the
  // sender declares fileLength, and stop before the 384 MB container runs out.
  private static readonly MAX_MEDIA_BYTES = 64 * 1024 * 1024;
  private static readonly TIMED_OUT = 'Media download timed out';

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

    // Baileys' fetch takes no abort signal: the deadline rejects a hung request and
    // destroys the stream, even one that arrives after it.
    const deadline = new AbortController();
    const timer = setTimeout(() => deadline.abort(), DOWNLOAD_TIMEOUT_MS);
    const download = downloadMediaMessage(
      message,
      'stream',
      {},
      {
        reuploadRequest: this.whatsapp.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );
    download.then(
      (stream) => deadline.signal.aborted && stream.destroy(),
      () => undefined,
    );
    try {
      const stream = await Promise.race([download, MediaHandler.expiry(deadline.signal)]);
      return await MediaHandler.read(stream, deadline.signal);
    } finally {
      clearTimeout(timer);
    }
  }

  private static expiry(deadline: AbortSignal): Promise<never> {
    return new Promise((_, reject) => {
      deadline.addEventListener('abort', () => reject(new Error(MediaHandler.TIMED_OUT)));
    });
  }

  private static async read(stream: Readable, deadline: AbortSignal): Promise<Buffer> {
    const stop = () => stream.destroy(new Error(MediaHandler.TIMED_OUT));
    deadline.addEventListener('abort', stop);
    const chunks: Buffer[] = [];
    let size = 0;
    try {
      for await (const chunk of stream) {
        size += chunk.length;
        if (size > MediaHandler.MAX_MEDIA_BYTES) {
          throw new Error(`Media is larger than ${MediaHandler.MAX_MEDIA_BYTES} bytes`);
        }
        chunks.push(chunk);
      }
    } finally {
      deadline.removeEventListener('abort', stop);
    }
    return Buffer.concat(chunks);
  }
}
