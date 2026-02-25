import type { WAMessage } from '@whiskeysockets/baileys';

export default class GetTextMessage {
  static run(data: WAMessage): string {
    return (
      data.message?.conversation ||
      data.message?.extendedTextMessage?.text ||
      data.message?.videoMessage?.caption ||
      data.message?.imageMessage?.caption ||
      data.message?.documentWithCaptionMessage?.message?.documentMessage?.caption ||
      ''
    );
  }
}
