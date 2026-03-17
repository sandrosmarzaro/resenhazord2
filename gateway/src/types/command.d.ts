import type { WAMessage } from '@whiskeysockets/baileys';

export interface CommandData extends WAMessage {
  text: string;
  expiration: number | undefined;
}
