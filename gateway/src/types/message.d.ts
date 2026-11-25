import type { AnyMessageContent, MiscMessageGenerationOptions } from '@whiskeysockets/baileys';

export interface Message {
  jid: string;
  content: AnyMessageContent;
  options?: MiscMessageGenerationOptions;
  // A WhatsApp audio sticker: no AnyMessageContent carries the audio.
  audioSticker?: { sticker: Buffer; audio: Buffer };
}
