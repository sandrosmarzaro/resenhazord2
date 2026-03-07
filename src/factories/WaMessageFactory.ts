import type { WAMessage, proto } from '@whiskeysockets/baileys';

type TextExtractor = (m: proto.IMessage) => string | undefined;
type ExpirationExtractor = (m: proto.IMessage) => number | undefined;

const TEXT_EXTRACTORS: Partial<Record<keyof proto.IMessage, TextExtractor>> = {
  conversation: (m) => m.conversation ?? undefined,
  extendedTextMessage: (m) => m.extendedTextMessage?.text ?? undefined,
  imageMessage: (m) => m.imageMessage?.caption ?? undefined,
  videoMessage: (m) => m.videoMessage?.caption ?? undefined,
  documentWithCaptionMessage: (m) =>
    m.documentWithCaptionMessage?.message?.documentMessage?.caption ?? undefined,
};

const EXPIRATION_EXTRACTORS: Partial<Record<keyof proto.IMessage, ExpirationExtractor>> = {
  extendedTextMessage: (m) => m.extendedTextMessage?.contextInfo?.expiration ?? undefined,
  imageMessage: (m) => m.imageMessage?.contextInfo?.expiration ?? undefined,
  videoMessage: (m) => m.videoMessage?.contextInfo?.expiration ?? undefined,
  documentWithCaptionMessage: (m) =>
    m.documentWithCaptionMessage?.message?.documentMessage?.contextInfo?.expiration ?? undefined,
};

export default class WaMessageFactory {
  static getText(message: WAMessage): string {
    const msg = message.message;
    if (!msg) return '';
    for (const [key, extract] of Object.entries(TEXT_EXTRACTORS)) {
      if (msg[key as keyof proto.IMessage]) {
        return extract!(msg) ?? '';
      }
    }
    return '';
  }

  static getExpiration(message: WAMessage): number | undefined {
    const msg = message.message;
    if (!msg) return undefined;
    for (const [key, extract] of Object.entries(EXPIRATION_EXTRACTORS)) {
      if (msg[key as keyof proto.IMessage]) {
        return extract!(msg);
      }
    }
    return undefined;
  }
}
