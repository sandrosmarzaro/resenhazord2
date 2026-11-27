import { RabbitMQContainer, type StartedRabbitMQContainer } from '@testcontainers/rabbitmq';
import { connect } from 'amqplib';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import logger from '../../src/infra/Logger.js';
import defaultTopology from '../../src/data/BrokerTopology.json' with { type: 'json' };
import RabbitBroker from '../../src/infra/RabbitBroker.js';
import type { BrokerTopology } from '../../src/types/brokerTopology.js';

// What the nodes declared before the exchanges existed (ADR 0004): the topology must
// redeclare each queue with exactly these arguments, or the broker answers
// PRECONDITION_FAILED.
const LEGACY_QUEUES: Record<string, Record<string, number | string>> = {
  commands: {},
  replies: {},
  wa_actions: {},
  wa_rpc: {},
  group_events: {},
  'commands.dlq': {},
  'commands.retry': {
    'x-message-ttl': 30_000,
    'x-dead-letter-exchange': '',
    'x-dead-letter-routing-key': 'commands',
  },
};

const BINDINGS = [
  ['resenhazord.commands', 'command.whatsapp', 'commands'],
  ['resenhazord.commands', 'wa.action.send_message', 'wa_actions'],
  ['resenhazord.commands', 'wa.rpc.group_metadata', 'wa_rpc'],
  ['resenhazord.events', 'reply.whatsapp', 'replies'],
  ['resenhazord.events', 'group.joined', 'group_events'],
];

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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redeclares the queues an old node declared', async () => {
    await declareLegacyQueues(url);
    const broker = new RabbitBroker();

    await broker.connect(url);
    await broker.close();

    await expect(declareLegacyQueues(url)).resolves.toBeUndefined();
  });

  it.each(BINDINGS)(
    'routes %s %s to the %s queue an old node reads',
    async (exchange, routingKey, queue) => {
      const broker = new RabbitBroker();
      await broker.connect(url);
      await purge(url, queue);

      await publishTo(url, exchange, routingKey);
      const received = await getOne(url, queue);

      await broker.close();
      expect(received).toBe('roteado');
    },
  );

  it('dead-letters a command past the delivery limit to the DLQ', async () => {
    const broker = new RabbitBroker();
    await broker.connect(url);
    await purge(url, 'commands.dlq');
    const crashes = await crashBeforeTheAck(url, 'commands.quorum');

    await publishTo(url, '', 'commands.quorum');
    const deadLetter = await waitForOne(url, 'commands.dlq');

    await crashes.close();
    await broker.close();
    expect(deadLetter).toBe('roteado');
  });

  it('publishes a durable message a consumer receives', async () => {
    const broker = new RabbitBroker({
      exchanges: [],
      deadLetterExchange: 'round_trip.dlx',
      queues: { round_trip: {} },
      bindings: [],
      deadLetterRoutes: {},
    });
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

  it('skips the ack when the channel closes while a consumer runs', async () => {
    const broker = new RabbitBroker();
    const publisher = new RabbitBroker();
    await broker.connect(url);
    await publisher.connect(url);
    await broker.consume('closing_q', () => broker.close());

    await publisher.publish('closing_q', Buffer.from('oi'));

    await vi.waitFor(() =>
      expect(logger.warn).toHaveBeenCalledWith({
        event: 'consume_ack_skipped',
        error: expect.stringContaining('Channel closed'),
      }),
    );
    await publisher.close();
  });

  it('skips the ack when the channel closes while an RPC handler runs', async () => {
    const broker = new RabbitBroker();
    const publisher = new RabbitBroker();
    await broker.connect(url);
    await publisher.connect(url);
    await broker.respondRpc('closing_rpc_q', async () => {
      await broker.close();
      return Buffer.from('tarde demais');
    });

    await publisher.publish('closing_rpc_q', Buffer.from('oi'));

    await vi.waitFor(() =>
      expect(logger.warn).toHaveBeenCalledWith({
        event: 'consume_ack_skipped',
        error: expect.stringContaining('Channel closed'),
      }),
    );
    await publisher.close();
  });
});

describe('RabbitBroker retry ladder', () => {
  // Milliseconds each step holds a rejected command here, instead of 5 s, 30 s, 2 m.
  const STEP_MS = [200, 400, 600];
  const LADDER = ['commands.retry.5s', 'commands.retry.30s', 'commands.retry.2m'];
  let container: StartedRabbitMQContainer;
  let url: string;

  beforeAll(async () => {
    container = await new RabbitMQContainer('rabbitmq:3.13').start();
    url = container.getAmqpUrl();
  }, 120_000);

  afterAll(async () => {
    await container.stop();
  });

  function shortLadder(): BrokerTopology {
    const queues: BrokerTopology['queues'] = { ...defaultTopology.queues };
    LADDER.forEach((queue, step) => {
      queues[queue] = { ...queues[queue], 'x-message-ttl': STEP_MS[step] };
    });
    return { ...defaultTopology, queues };
  }

  it('brings a rejected command back to the commands queue after its step', async () => {
    const broker = new RabbitBroker(shortLadder());
    await broker.connect(url);
    const core = await rejectingCore(url, 1);

    await publishTo(url, '', 'commands.quorum');
    const runs = await core.accepted;

    await core.close();
    await broker.close();
    expect(runs).toHaveLength(2);
    expect(runs[1] - runs[0]).toBeGreaterThanOrEqual(STEP_MS[0]);
  });

  it('sends a command rejected past the last step to the DLQ', async () => {
    const broker = new RabbitBroker(shortLadder());
    await broker.connect(url);
    await purge(url, 'commands.dlq');
    const core = await rejectingCore(url, Infinity);

    await publishTo(url, '', 'commands.quorum');
    const deadLetter = await waitForOne(url, 'commands.dlq');

    await core.close();
    await broker.close();
    expect(deadLetter).toBe('roteado');
    expect(core.runs).toHaveLength(LADDER.length + 1);
  });
});

// Stands in for the core: rejects the first `rejections` deliveries without requeue, as
// RetryRouter does for a retryable failure, then acks.
async function rejectingCore(url: string, rejections: number) {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  const runs: number[] = [];
  const accepted = new Promise<number[]>((resolve) => {
    void channel.consume('commands.quorum', (message) => {
      if (!message) return;
      runs.push(performance.now());
      if (runs.length <= rejections) {
        channel.nack(message, false, false);
        return;
      }
      channel.ack(message);
      resolve(runs);
    });
  });
  // Closing the channel first waits until the broker has taken the last ack.
  const close = async () => {
    await channel.close();
    await connection.close();
  };
  return { runs, accepted, close };
}

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

async function declareLegacyQueues(url: string): Promise<void> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  for (const [queue, args] of Object.entries(LEGACY_QUEUES)) {
    await channel.assertQueue(queue, { durable: true, arguments: args });
  }
  await connection.close();
}

async function publishTo(url: string, exchange: string, routingKey: string): Promise<void> {
  const connection = await connect(url);
  const channel = await connection.createConfirmChannel();
  channel.publish(exchange, routingKey, Buffer.from('roteado'));
  await channel.waitForConfirms();
  await connection.close();
}

// A core that dies before its ack hands the command back the same way.
async function crashBeforeTheAck(url: string, queue: string): Promise<{ close(): Promise<void> }> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  await channel.consume(queue, (message) => {
    if (message) channel.nack(message, false, true);
  });
  return connection;
}

async function waitForOne(url: string, queue: string): Promise<string> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  const body = await new Promise<string>((resolve) => {
    void channel.consume(
      queue,
      (message) => {
        if (message) resolve(message.content.toString());
      },
      { noAck: true },
    );
  });
  await connection.close();
  return body;
}

async function purge(url: string, queue: string): Promise<void> {
  const connection = await connect(url);
  const channel = await connection.createChannel();
  await channel.purgeQueue(queue);
  await connection.close();
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
