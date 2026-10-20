import type { BaileysEventMap } from '@whiskeysockets/baileys';
import Resenhazord2 from '../models/Resenhazord2.js';

// Baileys reports the bot being added to a group as groups.upsert, not as a
// group-participants.update 'add'.
export default class GroupsUpsertEvent {
  static async run(groups: BaileysEventMap['groups.upsert']): Promise<void> {
    for (const group of groups) {
      await Resenhazord2.groupEventPublisher.publish({ id: group.id, action: 'joined' });
    }
  }
}
