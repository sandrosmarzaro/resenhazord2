import type { WAMessage } from '@whiskeysockets/baileys';
import WaMessageFactory from '../factories/WaMessageFactory.js';

export default class GetGroupExpiration {
  static async run(data: WAMessage): Promise<number | undefined> {
    return WaMessageFactory.getExpiration(data);
  }
}
