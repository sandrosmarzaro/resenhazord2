import type { AnyMessageContent } from '@whiskeysockets/baileys';
import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';

export default class Reply {
  private readonly data: CommandData;

  private constructor(data: CommandData) {
    this.data = data;
  }

  static to(data: CommandData): Reply {
    return new Reply(data);
  }

  text(text: string): Message {
    return this.build({ text });
  }

  textWith(text: string, mentions: string[]): Message {
    return this.build({ text, mentions });
  }

  image(url: string, caption?: string): Message {
    return this.build({ image: { url }, viewOnce: true, ...(caption && { caption }) });
  }

  imageBuffer(buffer: Buffer, caption?: string): Message {
    return this.build({ image: buffer, viewOnce: true, ...(caption && { caption }) });
  }

  video(url: string, caption?: string): Message {
    return this.build({ video: { url }, viewOnce: true, ...(caption && { caption }) });
  }

  audio(url: string): Message {
    return this.build({ audio: { url }, viewOnce: true, mimetype: 'audio/mp4' });
  }

  sticker(buffer: Buffer): Message {
    return this.build({ sticker: buffer });
  }

  raw(content: AnyMessageContent): Message {
    return this.build(content);
  }

  private build(content: AnyMessageContent): Message {
    return {
      jid: this.data.key.remoteJid!,
      content,
      options: { quoted: this.data, ephemeralExpiration: this.data.expiration },
    };
  }
}
