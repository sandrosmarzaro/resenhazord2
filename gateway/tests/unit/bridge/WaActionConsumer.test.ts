import { describe, it, expect, vi } from 'vitest';

import WaActionConsumer from '../../../src/bridge/WaActionConsumer.js';
import type { MessageHandler } from '../../../src/ports/BrokerPort.js';
import { createMockBrokerPort } from '../../fixtures/factories/MockBrokerPort.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';

function actionCapturingBroker(): {
  broker: ReturnType<typeof createMockBrokerPort>;
  deliver: (action: unknown) => Promise<void>;
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
    deliver: (action) => handler(Buffer.from(JSON.stringify(action))),
  };
}

describe('WaActionConsumer', () => {
  it('consumes the wa_actions queue on start', async () => {
    const { broker } = actionCapturingBroker();
    await new WaActionConsumer(broker, createMockWhatsAppPort()).start();

    expect(broker.consume).toHaveBeenCalledWith('wa_actions', expect.any(Function));
  });

  it('applies a participant update', async () => {
    const { broker, deliver } = actionCapturingBroker();
    const whatsapp = createMockWhatsAppPort();
    await new WaActionConsumer(broker, whatsapp).start();

    await deliver({
      method: 'group_participants_update',
      jid: 'g@g.us',
      participants: ['u@s'],
      action: 'remove',
    });

    expect(whatsapp.groupParticipantsUpdate).toHaveBeenCalledWith('g@g.us', ['u@s'], 'remove');
  });

  it('decodes a base64 profile picture', async () => {
    const { broker, deliver } = actionCapturingBroker();
    const whatsapp = createMockWhatsAppPort();
    await new WaActionConsumer(broker, whatsapp).start();

    await deliver({
      method: 'update_profile_picture',
      jid: 'g@g.us',
      image: Buffer.from([1, 2, 3]).toString('base64'),
    });

    expect(whatsapp.updateProfilePicture).toHaveBeenCalledWith('g@g.us', Buffer.from([1, 2, 3]));
  });

  it('applies a presence update', async () => {
    const { broker, deliver } = actionCapturingBroker();
    const whatsapp = createMockWhatsAppPort();
    await new WaActionConsumer(broker, whatsapp).start();

    await deliver({ method: 'send_presence_update', type: 'composing', jid: 'g@g.us' });

    expect(whatsapp.sendPresenceUpdate).toHaveBeenCalledWith('composing', 'g@g.us');
  });
});
