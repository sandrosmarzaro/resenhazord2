import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { generateWAMessageContent, type WASocket } from '@whiskeysockets/baileys';
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

  describe('audio stickers', () => {
    const media = (name: string) =>
      readFileSync(new URL(`../../fixtures/media/${name}`, import.meta.url));
    const options = { ephemeralExpiration: 86400 };

    function uploadingSocket() {
      const sendMessage = vi.fn();
      const waUploadToServer = vi.fn().mockResolvedValue({
        mediaUrl: 'https://mmg.whatsapp.net/m',
        directPath: '/m',
      });
      const socket = { updateMediaMessage: vi.fn(), sendMessage, waUploadToServer };
      return { socket: socket as unknown as WASocket, sendMessage };
    }

    async function sentSticker(webp: string) {
      const { socket, sendMessage } = uploadingSocket();
      await new BaileysAdapter(socket).sendAudioSticker(
        'g@g.us',
        media(webp),
        media('silence.ogg'),
        options,
      );
      const [jid, content, sentOptions] = sendMessage.mock.calls[0];
      return { jid, content, sentOptions, sticker: content.forward.message.stickerMessage };
    }

    it('sends the sticker with its opus audio attached', async () => {
      const { jid, sentOptions, sticker } = await sentSticker('animated.webp');

      expect([jid, sentOptions, sticker.mimetype]).toEqual(['g@g.us', options, 'image/webp']);
      expect(sticker.audioMessage).toMatchObject({
        mimetype: 'audio/ogg; codecs=opus',
        url: 'https://mmg.whatsapp.net/m',
      });
    });

    it('marks an animated webp as animated', async () => {
      const { sticker } = await sentSticker('animated.webp');

      expect(sticker.isAnimated).toBe(true);
    });

    it('leaves a still webp unanimated', async () => {
      const { sticker } = await sentSticker('still.webp');

      expect(sticker.isAnimated).toBe(false);
    });

    // Sending through sendMessage keeps quoting and disappearing messages: Baileys
    // copies a forward of the bot's own message without marking it forwarded.
    it('goes out as an unforwarded sticker that keeps its audio', async () => {
      const { content } = await sentSticker('animated.webp');

      const message = await generateWAMessageContent(content, { upload: vi.fn() });

      expect(message.stickerMessage?.contextInfo).toEqual({});
      expect(message.stickerMessage?.audioMessage?.mimetype).toBe('audio/ogg; codecs=opus');
    });
  });
});
