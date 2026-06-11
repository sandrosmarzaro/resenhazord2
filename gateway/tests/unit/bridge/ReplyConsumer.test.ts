import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { WAMessage } from '@whiskeysockets/baileys';

import ReplyConsumer from '../../../src/bridge/ReplyConsumer.js';
import InFlightCommands from '../../../src/bridge/InFlightCommands.js';
import TypingIndicator from '../../../src/utils/TypingIndicator.js';
import type BrokerPort from '../../../src/ports/BrokerPort.js';
import type { MessageHandler } from '../../../src/ports/BrokerPort.js';
import type WhatsAppPort from '../../../src/ports/WhatsAppPort.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';

function brokerCapturingHandler(): {
  broker: BrokerPort;
  deliver: (envelope: unknown) => Promise<void>;
} {
  let handler: MessageHandler;
  const broker = createMockBrokerPort({
    consume: vi.fn().mockImplementation((_queue: string, given: MessageHandler) => {
      handler = given;
      return Promise.resolve();
    }),
  });
  return {
    broker,
    deliver: (envelope) => handler(Buffer.from(JSON.stringify(envelope))),
  };
}

interface Harness {
  broker: BrokerPort;
  whatsapp: WhatsAppPort;
  inFlight: InFlightCommands;
  deliver: (envelope: unknown) => Promise<void>;
}

async function startConsumer(): Promise<Harness> {
  const { broker, deliver } = brokerCapturingHandler();
  const whatsapp = createMockWhatsAppPort();
  const inFlight = new InFlightCommands();
  await new ReplyConsumer(broker, whatsapp, inFlight).start();
  return { broker, whatsapp, inFlight, deliver };
}

describe('ReplyConsumer', () => {
  beforeEach(() => {
    vi.spyOn(TypingIndicator, 'stop').mockResolvedValue(undefined);
  });

  it('consumes the replies queue on start', async () => {
    const { broker } = await startConsumer();

    expect(broker.consume).toHaveBeenCalledWith('replies', expect.any(Function));
  });

  it('pushes a text reply to WhatsApp', async () => {
    const { whatsapp, deliver } = await startConsumer();

    await deliver({
      id: 'corr-1',
      messages: [{ jid: 'g@g.us', content: { type: 'text', text: 'pong' } }],
    });

    expect(whatsapp.sendMessage).toHaveBeenCalledWith('g@g.us', { text: 'pong' }, {});
  });

  it('quotes the original tracked message and attaches expiration', async () => {
    const { whatsapp, inFlight, deliver } = await startConsumer();
    const original = { key: { id: 'ORIG_1', remoteJid: 'g@g.us' } } as WAMessage;
    inFlight.track('corr-1', 'g@g.us', original);

    await deliver({
      id: 'corr-1',
      messages: [
        {
          jid: 'g@g.us',
          content: { type: 'text', text: 'pong' },
          quoted_message_id: 'ORIG_1',
          expiration: 86400,
        },
      ],
    });

    expect(whatsapp.sendMessage).toHaveBeenCalledWith(
      'g@g.us',
      { text: 'pong' },
      { quoted: original, ephemeralExpiration: 86400 },
    );
  });

  it('skips the quote when the original message is no longer tracked', async () => {
    const { whatsapp, deliver } = await startConsumer();

    await deliver({
      id: 'corr-1',
      messages: [
        { jid: 'g@g.us', content: { type: 'text', text: 'pong' }, quoted_message_id: 'ORIG_1' },
      ],
    });

    expect(whatsapp.sendMessage).toHaveBeenCalledWith('g@g.us', { text: 'pong' }, {});
  });

  it('decodes a base64 buffer reply', async () => {
    const { whatsapp, deliver } = await startConsumer();

    const buffer = Buffer.from([9, 8, 7]);
    await deliver({
      id: 'corr-1',
      messages: [
        { jid: 'g@g.us', content: { type: 'image_buffer', buffer_b64: buffer.toString('base64') } },
      ],
    });

    const [, content] = (whatsapp.sendMessage as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(content.image).toEqual(buffer);
  });

  it('stops the typing indicator for a tracked command', async () => {
    const { inFlight, deliver } = await startConsumer();
    inFlight.track('corr-1', 'g@g.us', { key: { id: 'ORIG_1' } } as WAMessage);

    await deliver({
      id: 'corr-1',
      messages: [{ jid: 'g@g.us', content: { type: 'text', text: 'pong' } }],
    });

    expect(TypingIndicator.stop).toHaveBeenCalledWith('g@g.us');
  });

  it('stops typing on an empty terminal reply via the registry', async () => {
    const { whatsapp, inFlight, deliver } = await startConsumer();
    inFlight.track('corr-1', 'g@g.us', { key: { id: 'ORIG_1' } } as WAMessage);

    await deliver({ id: 'corr-1', messages: [] });

    expect(whatsapp.sendMessage).not.toHaveBeenCalled();
    expect(TypingIndicator.stop).toHaveBeenCalledWith('g@g.us');
  });
});
