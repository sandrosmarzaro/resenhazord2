import { connect as amqpConnect, type ConfirmChannel, type RecoveringChannelModel } from 'amqplib';

import type BrokerPort from '../ports/BrokerPort.js';

export default class RabbitBroker implements BrokerPort {
  private connection: RecoveringChannelModel | null = null;
  private channel: ConfirmChannel | null = null;

  async connect(url: string): Promise<void> {
    this.connection = await amqpConnect(url, { recovery: true });
    this.channel = await this.connection.createConfirmChannel();
  }

  async publish(queue: string, body: Buffer): Promise<void> {
    const channel = this.activeChannel();
    await channel.assertQueue(queue, { durable: true });
    channel.sendToQueue(queue, body, { persistent: true });
    await channel.waitForConfirms();
  }

  async close(): Promise<void> {
    if (this.connection) {
      await this.connection.close();
      this.connection = null;
      this.channel = null;
    }
  }

  private activeChannel(): ConfirmChannel {
    if (!this.channel) {
      throw new Error('Broker channel not connected; call connect() first');
    }
    return this.channel;
  }
}
