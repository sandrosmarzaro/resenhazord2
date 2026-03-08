import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@whiskeysockets/baileys', async (importOriginal) => {
  const original = await importOriginal<typeof import('@whiskeysockets/baileys')>();
  return {
    ...original,
    downloadMediaMessage: vi.fn().mockResolvedValue(Buffer.from('mock-buffer')),
    generateWAMessageFromContent: vi.fn().mockReturnValue({
      key: { remoteJid: '120363000000000001@g.us', fromMe: false, id: 'mock-id' },
      message: { stickerMessage: {} },
    }),
  };
});

import ExtrairCommand from '../../../src/commands/ExtrairCommand.js';
import { GroupCommandData, createMockWhatsAppPort } from '../../fixtures/index.js';

describe('ExtrairCommand', () => {
  let command: ExtrairCommand;

  describe('matches()', () => {
    beforeEach(() => {
      command = new ExtrairCommand();
    });

    it.each([
      [',extrair', true],
      [', extrair', true],
      [', EXTRAIR', true],
      [',extrair algo', false],
      ['extrair', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when no quoted sticker', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new ExtrairCommand(mockWhatsApp);
      const data = GroupCommandData.build({ text: ', extrair' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/sticker/i);
    });

    it('should return image buffer for static sticker', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new ExtrairCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', extrair' },
        { transient: { hasQuotedStickerMessage: true, quotedStickerIsAnimated: false } },
      );

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toHaveProperty('image');
      expect((messages[0].content as Record<string, unknown>).viewOnce).toBe(true);
    });

    it('should return video with gifPlayback for animated sticker', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new ExtrairCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', extrair' },
        { transient: { hasQuotedStickerMessage: true, quotedStickerIsAnimated: true } },
      );

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as Record<string, unknown>;
      expect(content).toHaveProperty('video');
      expect(content.gifPlayback).toBe(true);
    });

    it('should call downloadMediaMessage with reuploadRequest from adapter', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new ExtrairCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', extrair' },
        { transient: { hasQuotedStickerMessage: true } },
      );

      await command.run(data);

      const { downloadMediaMessage } = await import('@whiskeysockets/baileys');
      expect(downloadMediaMessage).toHaveBeenCalledWith(
        expect.anything(),
        'buffer',
        {},
        expect.objectContaining({ reuploadRequest: mockWhatsApp.updateMediaMessage }),
      );
    });

    it('should set quoted to the original data message', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new ExtrairCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', extrair' },
        { transient: { hasQuotedStickerMessage: true } },
      );

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toEqual(data);
    });
  });

  describe('regression', () => {
    it('whatsapp adapter is injected and not undefined', () => {
      const mockWhatsApp = createMockWhatsAppPort();
      const cmd = new ExtrairCommand(mockWhatsApp);
      expect((cmd as unknown as { whatsapp: unknown }).whatsapp).toBe(mockWhatsApp);
    });
  });
});
