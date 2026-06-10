import { describe, it, expect, vi } from 'vitest';

import ReplyConsumer from '../../../src/bridge/ReplyConsumer.js';
import type BrokerPort from '../../../src/ports/BrokerPort.js';
import type { MessageHandler } from '../../../src/ports/BrokerPort.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';

function brokerCapturingHandler(): {
  broker: BrokerPort;
  deliver: (envelope: unknown) => Promise<void>;
} {
  let handler: MessageHandler;
  const broker: BrokerPort = {
    connect: vi.fn(),
    publish: vi.fn(),
    consume: vi.fn().mockImplementation((_queue: string, given: MessageHandler) => {
      handler = given;
      return Promise.resolve();
    }),
    close: vi.fn(),
  };
  return {
    broker,
    deliver: (envelope) => handler(Buffer.from(JSON.stringify(envelope))),
  };
}

describe('ReplyConsumer', () => {
  it('consumes the replies queue on start', async () => {
    const { broker } = brokerCapturingHandler();
    const whatsapp = createMockWhatsAppPort();

    await new ReplyConsumer(broker, whatsapp).start();

    expect(broker.consume).toHaveBeenCalledWith('replies', expect.any(Function));
  });

  it('pushes a text reply to WhatsApp', async () => {
    const { broker, deliver } = brokerCapturingHandler();
    const whatsapp = createMockWhatsAppPort();
    await new ReplyConsumer(broker, whatsapp).start();

    await deliver({
      id: 'corr-1',
      messages: [{ jid: 'g@g.us', content: { type: 'text', text: 'pong' } }],
    });

    expect(whatsapp.sendMessage).toHaveBeenCalledWith('g@g.us', { text: 'pong' }, {});
  });

  it('attaches quoted and expiration options', async () => {
    const { broker, deliver } = brokerCapturingHandler();
    const whatsapp = createMockWhatsAppPort();
    await new ReplyConsumer(broker, whatsapp).start();

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
      { quoted: { key: { id: 'ORIG_1' } }, ephemeralExpiration: 86400 },
    );
  });

  it('decodes a base64 buffer reply', async () => {
    const { broker, deliver } = brokerCapturingHandler();
    const whatsapp = createMockWhatsAppPort();
    await new ReplyConsumer(broker, whatsapp).start();

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

  it('sends nothing for an empty terminal reply', async () => {
    const { broker, deliver } = brokerCapturingHandler();
    const whatsapp = createMockWhatsAppPort();
    await new ReplyConsumer(broker, whatsapp).start();

    await deliver({ id: 'corr-1', messages: [] });

    expect(whatsapp.sendMessage).not.toHaveBeenCalled();
  });
});
