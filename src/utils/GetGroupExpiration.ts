import type { WAMessage } from '@whiskeysockets/baileys';

export default class GetGroupExpiration {
  static async run(data: WAMessage): Promise<number | undefined> {
    return (
      data.message?.extendedTextMessage?.contextInfo?.expiration ||
      data.message?.imageMessage?.contextInfo?.expiration ||
      data.message?.videoMessage?.contextInfo?.expiration ||
      data.message?.documentWithCaptionMessage?.message?.documentMessage?.contextInfo?.expiration ||
      undefined
    );
  }
}
