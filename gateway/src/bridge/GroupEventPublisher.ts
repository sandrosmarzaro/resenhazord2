import type BrokerPort from '../ports/BrokerPort.js';

export default class GroupEventPublisher {
  private static readonly QUEUE = 'group_events';

  constructor(private readonly broker: BrokerPort) {}

  async publish(event: Record<string, unknown>): Promise<void> {
    await this.broker.publish(GroupEventPublisher.QUEUE, Buffer.from(JSON.stringify(event)));
  }
}
