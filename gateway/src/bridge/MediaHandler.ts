import type { WAMessage } from '@whiskeysockets/baileys';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import pino from 'pino';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import type { CommandData } from '../types/command.js';

export interface MediaInfo {
  type: 'image' | 'video' | 'audio' | 'sticker';
  source: 'direct' | 'quoted' | 'view_once';
  isAnimated?: boolean;
  caption?: string;
}

type AnyMsg = Record<string, Record<string, unknown> | undefined>;

const MEDIA_TYPES = ['imageMessage', 'videoMessage', 'audioMessage'] as const;

const VIEW_ONCE_WRAPPERS = [
  'viewOnceMessageV2',
  'viewOnceMessageV2Extension',
  'viewOnceMessage',
] as const;

const TYPE_MAP: Record<string, MediaInfo['type']> = {
  imageMessage: 'image',
  videoMessage: 'video',
  audioMessage: 'audio',
  stickerMessage: 'sticker',
};

const DOWNLOAD_TIMEOUT_MS = 50_000;

export default class MediaHandler {
  constructor(private readonly whatsapp: WhatsAppPort) {}

  detectMedia(data: CommandData): MediaInfo | null {
    const msg = data.message as AnyMsg | undefined;
    if (!msg) return null;

    for (const type of MEDIA_TYPES) {
      if (msg[type]) return { type: TYPE_MAP[type], source: 'direct' };
    }

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

    for (const type of MEDIA_TYPES) {
      const media = quoted[type];
      if (media) {
        return {
          type: TYPE_MAP[type],
          source: 'quoted',
          caption: (media.caption as string | undefined) ?? undefined,
        };
      }
    }

    for (const wrapper of VIEW_ONCE_WRAPPERS) {
      const inner = (quoted[wrapper] as AnyMsg | undefined)?.message as AnyMsg | undefined;
      if (!inner) continue;
      for (const type of MEDIA_TYPES) {
        const media = inner[type];
        if (media) {
          return {
            type: TYPE_MAP[type],
            source: 'view_once',
            caption: (media.caption as string | undefined) ?? undefined,
          };
        }
      }
    }

    for (const type of MEDIA_TYPES) {
      const media = quoted[type];
      if (media?.viewOnce) {
        return {
          type: TYPE_MAP[type],
          source: 'view_once',
          caption: (media.caption as string | undefined) ?? undefined,
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

      let actualMessage: proto.IMessage = quoted;

      if (source === 'view_once') {
        const quotedAny = quoted as AnyMsg;
        for (const wrapper of VIEW_ONCE_WRAPPERS) {
          const inner = (quotedAny[wrapper] as AnyMsg | undefined)?.message;
          if (inner) {
            actualMessage = inner as unknown as proto.IMessage;
            break;
          }
        }
      }

      message = generateWAMessageFromContent(
        stored.key.remoteJid!,
        actualMessage as proto.IMessage,
        {
          userJid: stored.key.remoteJid?.includes('@g.us')
            ? stored.key.participant!
            : stored.key.remoteJid!,
        },
      );
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

    return (await Promise.race([download, timeout])) as Buffer;
  }

  async createSticker(inputBuffer: Buffer, type: string = 'full'): Promise<Buffer> {
    const { Sticker } = await import('wa-sticker-formatter');
    const { path: ffmpegPath } = await import('@ffmpeg-installer/ffmpeg');
    const ffmpeg = await import('fluent-ffmpeg');
    ffmpeg.default.setFfmpegPath(ffmpegPath);
    const sticker = await new Sticker(inputBuffer)
      .setPack('Resenhazord2')
      .setAuthor('Resenha')
      .setType(type)
      .setCategories(['Resenha', 'Bot'])
      .setQuality(50)
      .build();
    return Buffer.from(sticker);
  }
}
