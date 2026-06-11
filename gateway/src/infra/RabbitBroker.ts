import {
  connect as amqpConnect,
  type Channel,
  type ConfirmChannel,
  type ConsumeMessage,
  type RecoveringChannelModel,
} from 'amqplib';

import type BrokerPort from '../ports/BrokerPort.js';
import type { MessageHandler, RpcHandler } from '../ports/BrokerPort.js';
import logger from './Logger.js';

export default class RabbitBroker implements BrokerPort {
  private connection: RecoveringChannelModel | null = null;
  private channel: ConfirmChannel | null = null;
  private consumeChannel: Channel | null = null;

  async connect(url: string): Promise<void> {
    this.connection = await amqpConnect(url, { recovery: true });
    this.channel = await this.connection.createConfirmChannel();
    this.consumeChannel = await this.connection.createChannel();
  }

  async publish(queue: string, body: Buffer): Promise<void> {
    const channel = this.activeChannel();
    await channel.assertQueue(queue, { durable: true });
    channel.sendToQueue(queue, body, { persistent: true });
    await channel.waitForConfirms();
  }

  async consume(queue: string, handler: MessageHandler): Promise<void> {
    const channel = this.activeConsumeChannel();
    await channel.assertQueue(queue, { durable: true });
    await channel.consume(queue, (message) => {
      void this.dispatch(channel, handler, message);
    });
  }

  async respondRpc(queue: string, handler: RpcHandler): Promise<void> {
    const channel = this.activeConsumeChannel();
    await channel.assertQueue(queue, { durable: true });
    await channel.consume(queue, (message) => {
      void this.reply(channel, handler, message);
    });
  }

  async close(): Promise<void> {
    if (this.connection) {
      await this.connection.close();
      this.connection = null;
      this.channel = null;
      this.consumeChannel = null;
    }
  }

  private async dispatch(
    channel: Channel,
    handler: MessageHandler,
    message: ConsumeMessage | null,
  ): Promise<void> {
    if (!message) return;
    try {
      await handler(message.content);
    } catch (error) {
      logger.error({ event: 'consume_handler_error', error: String(error) });
    } finally {
      channel.ack(message);
    }
  }

  private async reply(
    channel: Channel,
    handler: RpcHandler,
    message: ConsumeMessage | null,
  ): Promise<void> {
    if (!message) return;
    const { correlationId, replyTo } = message.properties;
    try {
      const result = await handler(message.content);
      if (replyTo) channel.sendToQueue(replyTo, result, { correlationId });
    } catch (error) {
      logger.error({ event: 'rpc_handler_error', error: String(error) });
    } finally {
      channel.ack(message);
    }
  }

  private activeChannel(): ConfirmChannel {
    if (!this.channel) {
      throw new Error('Broker channel not connected; call connect() first');
    }
    return this.channel;
  }

  private activeConsumeChannel(): Channel {
    if (!this.consumeChannel) {
      throw new Error('Broker channel not connected; call connect() first');
    }
    return this.consumeChannel;
  }
}
