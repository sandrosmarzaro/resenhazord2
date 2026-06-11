import { describe, it, expect } from 'vitest';

import GroupEventPublisher from '../../../src/bridge/GroupEventPublisher.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';

describe('GroupEventPublisher', () => {
  it('publishes the serialized event to the group_events queue', async () => {
    const broker = createMockBrokerPort();
    const publisher = new GroupEventPublisher(broker);

    const event = { id: 'g@g.us', action: 'promote', participants: [] };
    await publisher.publish(event);

    expect(broker.publish).toHaveBeenCalledWith('group_events', Buffer.from(JSON.stringify(event)));
  });
});
