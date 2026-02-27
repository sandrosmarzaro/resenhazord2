import type { AnyMessageContent, MiscMessageGenerationOptions } from '@whiskeysockets/baileys';

export interface Message {
  jid: string;
  content: AnyMessageContent;
  options?: MiscMessageGenerationOptions;
}
