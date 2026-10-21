import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

// The bot runs on a regular WhatsApp account, so people call it. Only 1:1 calls reach
// Baileys: group calls ring the phone but never arrive at a linked device.
export default class CallEvent {
  private static readonly NOTICE =
    'Sou um bot, não atendo ligação 🤖 Manda *,menu* pra ver o que eu faço.';

  static async run(calls: BaileysEventMap['call']): Promise<void> {
    for (const call of calls.filter((update) => update.status === 'offer')) {
      await Resenhazord2.adapter!.rejectCall(call.id, call.from);
      await Resenhazord2.adapter!.sendMessage(call.from, { text: CallEvent.NOTICE });
    }
  }
}
