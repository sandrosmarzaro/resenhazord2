import { describe, it, expect, vi } from 'vitest';

import GroupEventPublisher from '../../../src/bridge/GroupEventPublisher.js';
import type BrokerPort from '../../../src/ports/BrokerPort.js';

describe('GroupEventPublisher', () => {
  it('publishes the serialized event to the group_events queue', async () => {
    const broker: BrokerPort = {
      connect: vi.fn(),
      publish: vi.fn().mockResolvedValue(undefined),
      consume: vi.fn(),
      close: vi.fn(),
    };
    const publisher = new GroupEventPublisher(broker);

    const event = { id: 'g@g.us', action: 'promote', participants: [] };
    await publisher.publish(event);

    expect(broker.publish).toHaveBeenCalledWith('group_events', Buffer.from(JSON.stringify(event)));
  });
});
