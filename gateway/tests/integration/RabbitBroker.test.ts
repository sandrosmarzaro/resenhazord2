import { RabbitMQContainer, type StartedRabbitMQContainer } from '@testcontainers/rabbitmq';
import { connect } from 'amqplib';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import RabbitBroker from '../../src/infra/RabbitBroker.js';

describe('RabbitBroker', () => {
  let container: StartedRabbitMQContainer;
  let url: string;

  beforeAll(async () => {
    container = await new RabbitMQContainer('rabbitmq:3.13').start();
    url = container.getAmqpUrl();
  }, 120_000);

  afterAll(async () => {
    await container.stop();
  });

  it('publishes a durable message a consumer receives', async () => {
    const broker = new RabbitBroker();
    await broker.connect(url);

    await broker.publish('round_trip', Buffer.from('ola mundo'));
    const received = await getOne(url, 'round_trip');

    await broker.close();

    expect(received).toBe('ola mundo');
  });

  it('delivers published messages to a registered consumer', async () => {
    const broker = new RabbitBroker();
    await broker.connect(url);

    const received: string[] = [];
    let resolve: () => void;
    const done = new Promise<void>((r) => {
      resolve = r;
    });
    await broker.consume('consume_q', async (body) => {
      received.push(body.toString());
      resolve();
    });

    await broker.publish('consume_q', Buffer.from('oi'));
    await done;
    await broker.close();

    expect(received).toEqual(['oi']);
  });

  it('responds to an RPC request on the reply queue', async () => {
    const broker = new RabbitBroker();
    await broker.connect(url);
    await broker.respondRpc('rpc_q', async (body) => {
      const request = JSON.parse(body.toString());
      return Buffer.from(JSON.stringify({ echo: request.value }));
    });

    const reply = await rpcRequest(url, 'rpc_q', { value: 42 });

    await broker.close();
    expect(reply).toEqual({ echo: 42 });
  });
});

async function rpcRequest(url: string, queue: string, payload: unknown): Promise<unknown> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  const { queue: replyTo } = await channel.assertQueue('', { exclusive: true });
  const correlationId = 'corr-test';

  const reply = new Promise<unknown>((resolve) => {
    channel
      .consume(
        replyTo,
        (message) => {
          if (message?.properties.correlationId === correlationId) {
            resolve(JSON.parse(message.content.toString()));
          }
        },
        { noAck: true },
      )
      .catch(() => {});
  });

  await channel.assertQueue(queue, { durable: true });
  channel.sendToQueue(queue, Buffer.from(JSON.stringify(payload)), { correlationId, replyTo });

  const result = await reply;
  await connection.close();
  return result;
}

async function getOne(url: string, queue: string): Promise<string> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  await channel.assertQueue(queue, { durable: true });
  const message = await channel.get(queue, { noAck: true });
  await connection.close();
  if (message === false) throw new Error('expected a message');
  return message.content.toString();
}
