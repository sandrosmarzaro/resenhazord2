import { describe, it, expect, vi } from 'vitest';

import WaRpcConsumer from '../../../src/bridge/WaRpcConsumer.js';
import type { RpcHandler } from '../../../src/ports/BrokerPort.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';

function rpcCapturingBroker(): {
  broker: ReturnType<typeof createMockBrokerPort>;
  call: (request: unknown) => Promise<unknown>;
} {
  let handler: RpcHandler;
  const broker = createMockBrokerPort({
    respondRpc: vi.fn().mockImplementation((_queue: string, given: RpcHandler) => {
      handler = given;
      return Promise.resolve();
    }),
  });
  return {
    broker,
    call: async (request) => {
      const reply = await handler(Buffer.from(JSON.stringify(request)));
      return JSON.parse(reply.toString());
    },
  };
}

describe('WaRpcConsumer', () => {
  it('responds to the wa_rpc queue on start', async () => {
    const { broker } = rpcCapturingBroker();
    await new WaRpcConsumer(broker, createMockWhatsAppPort()).start();

    expect(broker.respondRpc).toHaveBeenCalledWith('wa_rpc', expect.any(Function));
  });

  it('resolves on_whatsapp through the WhatsApp port', async () => {
    const { broker, call } = rpcCapturingBroker();
    const whatsapp = createMockWhatsAppPort({
      onWhatsApp: vi.fn().mockResolvedValue([{ exists: true, jid: '5511@s.whatsapp.net' }]),
    });
    await new WaRpcConsumer(broker, whatsapp).start();

    const reply = await call({ method: 'on_whatsapp', jids: ['5511'] });

    expect(whatsapp.onWhatsApp).toHaveBeenCalledWith('5511');
    expect(reply).toEqual({ results: [{ exists: true, jid: '5511@s.whatsapp.net' }] });
  });

  it('resolves group_metadata through the WhatsApp port', async () => {
    const { broker, call } = rpcCapturingBroker();
    const whatsapp = createMockWhatsAppPort({
      groupMetadata: vi.fn().mockResolvedValue({ id: 'g@g.us', subject: 'Resenha' }),
    });
    await new WaRpcConsumer(broker, whatsapp).start();

    const reply = await call({ method: 'group_metadata', jid: 'g@g.us' });

    expect(whatsapp.groupMetadata).toHaveBeenCalledWith('g@g.us');
    expect(reply).toEqual({ id: 'g@g.us', subject: 'Resenha' });
  });
});
