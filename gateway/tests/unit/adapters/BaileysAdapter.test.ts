import { describe, it, expect, vi } from 'vitest';
import type { WASocket } from '@whiskeysockets/baileys';
import BaileysAdapter from '../../../src/adapters/BaileysAdapter.js';

describe('BaileysAdapter', () => {
  it('rejects a call through the socket', async () => {
    const rejectCall = vi.fn();
    // Only the members the adapter touches; a real WASocket needs a live connection.
    const socket = { updateMediaMessage: vi.fn(), rejectCall } as unknown as WASocket;

    await new BaileysAdapter(socket).rejectCall('CALL-1', 'caller@lid');

    expect(rejectCall).toHaveBeenCalledWith('CALL-1', 'caller@lid');
  });

  it('marks messages read through the socket', async () => {
    const readMessages = vi.fn();
    const socket = { updateMediaMessage: vi.fn(), readMessages } as unknown as WASocket;
    const keys = [{ remoteJid: 'g@g.us', id: 'MSG-1', participant: 'u@lid' }];

    await new BaileysAdapter(socket).readMessages(keys);

    expect(readMessages).toHaveBeenCalledWith(keys);
  });
});
