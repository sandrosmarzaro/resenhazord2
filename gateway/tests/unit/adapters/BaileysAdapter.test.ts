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

  it('posts content as a group status authored by the bot', async () => {
    const relayMessage = vi.fn();
    const socket = {
      updateMediaMessage: vi.fn(),
      relayMessage,
      waUploadToServer: vi.fn(),
      user: { id: '5527999999999:3@s.whatsapp.net', lid: '189129606340826:3@lid' },
    } as unknown as WASocket;

    await new BaileysAdapter(socket).sendGroupStatus('g@g.us', { text: 'oi' });

    const [jid, message, options] = relayMessage.mock.calls[0];
    const text = message.groupStatusMessageV2.message.extendedTextMessage;
    expect([jid, options, text.text]).toEqual(['g@g.us', {}, 'oi']);
    expect(text.contextInfo.statusAttributions[0].groupStatus.authorJid).toBe(
      '189129606340826@lid',
    );
  });

  it("mutes a chat for good, WhatsApp's 'Always'", async () => {
    const chatModify = vi.fn();
    const socket = { updateMediaMessage: vi.fn(), chatModify } as unknown as WASocket;

    await new BaileysAdapter(socket).muteChat('g@g.us');

    expect(chatModify).toHaveBeenCalledWith({ mute: -1 }, 'g@g.us');
  });
});
