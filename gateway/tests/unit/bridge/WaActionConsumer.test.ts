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

  it('sends a message', async () => {
    const { broker, deliver } = actionCapturingBroker();
    const whatsapp = createMockWhatsAppPort();
    await new WaActionConsumer(broker, whatsapp).start();

    await deliver({ method: 'send_message', jid: 'g@g.us', content: { text: 'oi' }, options: {} });

    expect(whatsapp.sendMessage).toHaveBeenCalledWith('g@g.us', { text: 'oi' }, {});
  });

  it('updates subject and description', async () => {
    const { broker, deliver } = actionCapturingBroker();
    const whatsapp = createMockWhatsAppPort();
    await new WaActionConsumer(broker, whatsapp).start();

    await deliver({ method: 'group_update_subject', jid: 'g@g.us', subject: 'Resenha' });
    await deliver({ method: 'group_update_description', jid: 'g@g.us', description: 'desc' });

    expect(whatsapp.groupUpdateSubject).toHaveBeenCalledWith('g@g.us', 'Resenha');
    expect(whatsapp.groupUpdateDescription).toHaveBeenCalledWith('g@g.us', 'desc');
  });

  it('throws on an unknown action', async () => {
    const { broker, deliver } = actionCapturingBroker();
    await new WaActionConsumer(broker, createMockWhatsAppPort()).start();

    await expect(deliver({ method: 'nope', jid: 'g@g.us' })).rejects.toThrow('Unknown wa_action');
  });
});
