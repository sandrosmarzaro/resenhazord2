import type { AnyMessageContent, WAMessage } from '@whiskeysockets/baileys';
import type { Message } from '../types/message.js';
import injectStickerExif from '../utils/StickerExif.js';

// Reply messages arrive as dynamic JSON from the broker, so every field read here is
// a narrowing cast — the same shape the WS deserializer (PythonBridge) handled from
// binary frames, with buffers now base64-inline instead.
type ContentDict = Record<string, unknown>;
type Deserializer = (content: ContentDict) => AnyMessageContent | Promise<AnyMessageContent>;

export default class ReplyDeserializer {
  static async toMessage(raw: ContentDict): Promise<Message> {
    const content = raw.content as ContentDict;
    const deserializer = ReplyDeserializer.deserializers()[content.type as string];
    const deserialized: AnyMessageContent = deserializer
      ? await deserializer(content)
      : { text: `Unknown content type: ${content.type as string}` };

    const message: Message = { jid: raw.jid as string, content: deserialized };
    const options = ReplyDeserializer.options(raw);
    if (options) message.options = options;
    return message;
  }

  private static options(raw: ContentDict): Message['options'] | null {
    const options: Record<string, unknown> = {};
    if (raw.quoted_message_id) {
      options.quoted = { key: { id: raw.quoted_message_id as string } } as WAMessage;
    }
    if (raw.expiration) options.ephemeralExpiration = raw.expiration as number;
    return Object.keys(options).length > 0 ? (options as Message['options']) : null;
  }

  private static buffer(content: ContentDict): Buffer {
    return Buffer.from(content.buffer_b64 as string, 'base64');
  }

  private static deserializers(): Record<string, Deserializer> {
    const buf = ReplyDeserializer.buffer;
    return {
      text: (c) =>
        c.mentions
          ? { text: c.text as string, mentions: c.mentions as string[] }
          : { text: c.text as string },
      image: (c) => ({
        image: { url: c.url as string },
        viewOnce: c.view_once as boolean,
        caption: c.caption as string | undefined,
      }),
      image_buffer: (c) => ({
        image: buf(c),
        viewOnce: c.view_once as boolean,
        caption: c.caption as string | undefined,
      }),
      video: (c) => ({
        video: { url: c.url as string },
        viewOnce: c.view_once as boolean,
        caption: c.caption as string | undefined,
      }),
      video_buffer: (c) => ({
        video: buf(c),
        viewOnce: false,
        gifPlayback: (c.gif_playback as boolean) ?? false,
        caption: c.caption as string | undefined,
      }),
      audio: (c) => ({
        audio: { url: c.url as string },
        viewOnce: c.view_once as boolean,
        mimetype: (c.mimetype as string) ?? 'audio/mp4',
      }),
      audio_buffer: (c) => ({
        audio: buf(c),
        mimetype: (c.mimetype as string) ?? 'audio/mp4',
      }),
      sticker: async (c) => {
        const webp = buf(c);
        const pack = (c.pack as string) ?? '';
        const author = (c.author as string) ?? '';
        if (pack || author) return { sticker: await injectStickerExif(webp, pack, author) };
        return { sticker: webp };
      },
      raw: (c) => c.content as AnyMessageContent,
    };
  }
}
