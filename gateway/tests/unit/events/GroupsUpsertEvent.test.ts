import { describe, it, expect, vi, afterEach } from 'vitest';
import GroupsUpsertEvent from '../../../src/events/GroupsUpsertEvent.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import { GroupMetadataFactory } from '../../fixtures/factories/GroupMetadataFactory.js';

describe('GroupsUpsertEvent', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('publishes a joined event for each group the bot enters', async () => {
    const publish = vi.spyOn(Resenhazord2.groupEventPublisher, 'publish').mockResolvedValue();

    await GroupsUpsertEvent.run([
      GroupMetadataFactory.build({ id: 'first@g.us' }),
      GroupMetadataFactory.build({ id: 'second@g.us' }),
    ]);

    expect(publish.mock.calls).toEqual([
      [{ id: 'first@g.us', action: 'joined' }],
      [{ id: 'second@g.us', action: 'joined' }],
    ]);
  });

  // Joining a community group arrives as one batch: its announcement group, the group
  // itself and the community. Only the regular group is a chat the bot can greet.
  it('greets only the regular group of a community batch', async () => {
    const publish = vi.spyOn(Resenhazord2.groupEventPublisher, 'publish').mockResolvedValue();
    const community = 'community@g.us';

    await GroupsUpsertEvent.run([
      GroupMetadataFactory.build({
        id: 'announce@g.us',
        isCommunityAnnounce: true,
        linkedParent: community,
      }),
      GroupMetadataFactory.build({ id: 'general@g.us', linkedParent: community }),
      GroupMetadataFactory.build({ id: community, isCommunity: true }),
    ]);

    expect(publish.mock.calls).toEqual([[{ id: 'general@g.us', action: 'joined' }]]);
  });
});
