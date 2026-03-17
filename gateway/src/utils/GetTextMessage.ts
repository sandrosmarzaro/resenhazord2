import type { WAMessage } from '@whiskeysockets/baileys';
import WaMessageFactory from '../factories/WaMessageFactory.js';

export default class GetTextMessage {
  static run(data: WAMessage): string {
    return WaMessageFactory.getText(data);
  }
}
