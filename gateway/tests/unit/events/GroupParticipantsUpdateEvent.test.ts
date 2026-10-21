import { describe, it, expect, vi, afterEach } from 'vitest';
import GroupParticipantsUpdateEvent from '../../../src/events/GroupParticipantsUpdateEvent.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';

describe('GroupParticipantsUpdateEvent', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('publishes participants as Baileys reports them, LID with the PN alongside', async () => {
    const publish = vi.spyOn(Resenhazord2.groupEventPublisher, 'publish').mockResolvedValue();
    const participant = { id: 'bot-lid@lid', phoneNumber: 'bot@s.whatsapp.net', admin: null };

    await GroupParticipantsUpdateEvent.run({
      id: 'group@g.us',
      author: 'admin-lid@lid',
      participants: [participant],
      action: 'promote',
    });

    expect(publish).toHaveBeenCalledWith({
      id: 'group@g.us',
      action: 'promote',
      participants: [participant],
    });
  });
});
