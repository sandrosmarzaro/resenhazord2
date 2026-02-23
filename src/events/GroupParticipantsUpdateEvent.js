import StealGroupService from '../services/StealGroupService.js';

export default class GroupParticipantsUpdateEvent {
  static async run(data) {
    const { RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID } = process.env;
    if (![RESENHA_JID, RESENHAZORD2_JID, RESENHA_TEST_LID].includes(data.id)) {
      return;
    }
    await StealGroupService.run(data);
  }
}
