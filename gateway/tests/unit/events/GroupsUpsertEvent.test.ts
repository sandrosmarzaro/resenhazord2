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
});
