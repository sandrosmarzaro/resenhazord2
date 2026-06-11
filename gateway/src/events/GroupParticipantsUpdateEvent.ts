import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class GroupParticipantsUpdateEvent {
  static async run(data: BaileysEventMap['group-participants.update']): Promise<void> {
    await Resenhazord2.groupEventPublisher.publish({
      id: data.id,
      action: data.action,
      participants: data.participants.map((id) => ({ id })),
    });
  }
}
