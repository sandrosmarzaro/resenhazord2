import type { BaileysEventMap } from '@whiskeysockets/baileys';
import StealGroupService from '../services/StealGroupService.js';

export default class GroupParticipantsUpdateEvent {
  static async run(data: BaileysEventMap['group-participants.update']): Promise<void> {
    const { RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID } = process.env;
    if (![RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID].includes(data.id)) {
      return;
    }
    await StealGroupService.run(data);
  }
}
