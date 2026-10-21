import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { WACallEvent, WACallUpdateType } from '@whiskeysockets/baileys';
import CallEvent from '../../../src/events/CallEvent.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';
import { createMockWhatsAppPort } from '../../fixtures/factories/MockWhatsAppPort.js';
import type WhatsAppPort from '../../../src/ports/WhatsAppPort.js';

// Shape captured from a real 1:1 call: `from` is the caller's LID, the PN rides in callerPn.
function call(status: WACallUpdateType): WACallEvent {
  return {
    chatId: 'caller@lid',
    from: 'caller@lid',
    callerPn: 'caller@s.whatsapp.net',
    id: 'CALL-1',
    date: new Date(),
    offline: false,
    status,
    isVideo: false,
    isGroup: false,
  };
}

describe('CallEvent', () => {
  let whatsapp: WhatsAppPort;

  beforeEach(() => {
    whatsapp = createMockWhatsAppPort();
    Resenhazord2.adapter = whatsapp;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('rejects an incoming call', async () => {
    await CallEvent.run([call('offer')]);

    expect(whatsapp.rejectCall).toHaveBeenCalledWith('CALL-1', 'caller@lid');
  });

  it('tells the caller to use the menu instead', async () => {
    await CallEvent.run([call('offer')]);

    expect(whatsapp.sendMessage).toHaveBeenCalledWith('caller@lid', {
      text: expect.stringContaining(',menu'),
    });
  });

  it('ignores the updates that follow the offer', async () => {
    await CallEvent.run([call('relaylatency'), call('terminate')]);

    expect(whatsapp.rejectCall).not.toHaveBeenCalled();
    expect(whatsapp.sendMessage).not.toHaveBeenCalled();
  });
});
