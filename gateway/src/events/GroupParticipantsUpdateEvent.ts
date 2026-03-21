import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class GroupParticipantsUpdateEvent {
  static run(data: BaileysEventMap['group-participants.update']): void {
    Resenhazord2.bridge.sendGroupEvent({
      id: data.id,
      action: data.action,
      participants: data.participants.map((id) => ({ id })),
    });
  }
}
