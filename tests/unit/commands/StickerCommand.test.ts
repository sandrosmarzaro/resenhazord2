import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@whiskeysockets/baileys', async (importOriginal) => {
  const original = await importOriginal<typeof import('@whiskeysockets/baileys')>();
  return {
    ...original,
    downloadMediaMessage: vi.fn().mockResolvedValue(Buffer.from('mock-buffer')),
    generateWAMessageFromContent: vi.fn().mockReturnValue({
      key: { remoteJid: '120363000000000001@g.us', fromMe: false, id: 'mock-id' },
      message: { imageMessage: {} },
    }),
  };
});

vi.mock('wa-sticker-formatter', () => {
  class Sticker {
    setPack() {
      return this;
    }
    setAuthor() {
      return this;
    }
    setType() {
      return this;
    }
    setCategories() {
      return this;
    }
    setQuality() {
      return this;
    }
    build() {
      return Promise.resolve(Buffer.from('mock-sticker'));
    }
  }
  return { Sticker };
});

vi.mock('fluent-ffmpeg', () => ({ default: { setFfmpegPath: vi.fn() } }));
vi.mock('@ffmpeg-installer/ffmpeg', () => ({ path: '/mock/ffmpeg' }));

import StickerCommand from '../../../src/commands/StickerCommand.js';
import { GroupCommandData, createMockWhatsAppPort } from '../../fixtures/index.js';

describe('StickerCommand', () => {
  let command: StickerCommand;

  describe('matches()', () => {
    beforeEach(() => {
      command = new StickerCommand();
    });

    it.each([
      [',stic', true],
      [', stic', true],
      [', STIC', true],
      [', stic crop', true],
      [', stic full', true],
      [', sticker', false],
      ['stic', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when no media is attached', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new StickerCommand(mockWhatsApp);
      const data = GroupCommandData.build({ text: ', stic' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/imagem|gif/i);
    });

    it('should return sticker when image media is attached', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new StickerCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', stic' },
        { transient: { hasImageMessage: true } },
      );

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toHaveProperty('sticker');
    });

    it('should call downloadMediaMessage with reuploadRequest from adapter', async () => {
      const mockWhatsApp = createMockWhatsAppPort();
      command = new StickerCommand(mockWhatsApp);
      const data = GroupCommandData.build(
        { text: ', stic' },
        { transient: { hasImageMessage: true } },
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
  });

  describe('regression', () => {
    it('whatsapp adapter is injected and not undefined', () => {
      const mockWhatsApp = createMockWhatsAppPort();
      const cmd = new StickerCommand(mockWhatsApp);
      expect((cmd as unknown as { whatsapp: unknown }).whatsapp).toBe(mockWhatsApp);
    });
  });
});
