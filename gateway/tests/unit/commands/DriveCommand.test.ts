import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('@whiskeysockets/baileys', async (importOriginal) => {
  const original = await importOriginal<typeof import('@whiskeysockets/baileys')>();
  return {
    ...original,
    downloadMediaMessage: vi.fn().mockResolvedValue(Buffer.from('mock-buffer')),
  };
});

import { downloadMediaMessage } from '@whiskeysockets/baileys';
import DriveCommand from '../../../src/commands/DriveCommand.js';
import DiscordService from '../../../src/clients/DiscordService.js';
import {
  GroupCommandData,
  PrivateCommandData,
  createMockWhatsAppPort,
} from '../../fixtures/index.js';

const mockDownload = downloadMediaMessage as ReturnType<typeof vi.fn>;

function createMockDiscordService(): DiscordService {
  return {
    getChannels: vi.fn().mockResolvedValue([]),
    createCategory: vi.fn().mockResolvedValue({ id: 'cat-1', name: '2026', type: 4 }),
    createChannel: vi
      .fn()
      .mockResolvedValue({ id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' }),
    uploadMedia: vi.fn().mockResolvedValue(undefined),
  } as unknown as DiscordService;
}

describe('DriveCommand', () => {
  let command: DriveCommand;
  let mockWhatsApp: ReturnType<typeof createMockWhatsAppPort>;
  let mockDiscord: DiscordService;

  beforeEach(() => {
    mockWhatsApp = createMockWhatsAppPort();
    mockDiscord = createMockDiscordService();
    command = new DriveCommand(mockWhatsApp, mockDiscord);
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',drive 2026 churrasco', true],
      [', drive 2026 churrasco', true],
      [',DRIVE 2026 churrasco', true],
      [',drive', false],
      ['drive 2026 churrasco', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('groupOnly restriction', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ',drive 2026 churrasco' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/grupo/i);
    });
  });

  describe('run() - no media', () => {
    it('should return error when no media in message or quoted', async () => {
      const data = GroupCommandData.build({ text: ',drive 2026 churrasco' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/mídia/i);
    });
  });

  describe('run() - category/channel not found', () => {
    it('should return error when category not found without new flag', async () => {
      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasImageMessage: true } },
      );
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([]);

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/2026/);
      expect(content.text).toMatch(/não encontrad/i);
    });

    it('should return error when channel not found without new flag', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([existingCategory]);
      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasImageMessage: true } },
      );

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/churrasco/);
      expect(content.text).toMatch(/não encontrad/i);
    });
  });

  describe('run() - new flag', () => {
    it('should create category and channel when both missing with new flag', async () => {
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([]);
      (mockDiscord.createCategory as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'cat-1',
        name: '2026',
        type: 4,
      });
      (mockDiscord.createChannel as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'ch-1',
        name: 'churrasco',
        type: 0,
        parent_id: 'cat-1',
      });
      mockDownload.mockResolvedValue(Buffer.from('img-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco new' },
        { transient: { hasImageMessage: true } },
      );

      const messages = await command.run(data);

      expect(mockDiscord.createCategory).toHaveBeenCalledWith('2026');
      expect(mockDiscord.createChannel).toHaveBeenCalledWith('churrasco', 'cat-1');
      expect(mockDiscord.uploadMedia).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('2026');
      expect(content.text).toContain('churrasco');
    });

    it('should not create category when it exists, only create channel', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([existingCategory]);
      (mockDiscord.createChannel as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'ch-1',
        name: 'churrasco',
        type: 0,
        parent_id: 'cat-1',
      });
      mockDownload.mockResolvedValue(Buffer.from('img-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco new' },
        { transient: { hasImageMessage: true } },
      );

      await command.run(data);

      expect(mockDiscord.createCategory).not.toHaveBeenCalled();
      expect(mockDiscord.createChannel).toHaveBeenCalledWith('churrasco', 'cat-1');
    });
  });

  describe('run() - successful upload', () => {
    it('should upload image and return success message', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      const existingChannel = { id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([
        existingCategory,
        existingChannel,
      ]);
      mockDownload.mockResolvedValue(Buffer.from('img-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasImageMessage: true } },
      );

      const messages = await command.run(data);

      expect(mockDiscord.uploadMedia).toHaveBeenCalledWith(
        'ch-1',
        expect.any(Buffer),
        expect.stringMatching(/^image_\d+\.jpg$/),
      );
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('2026');
      expect(content.text).toContain('churrasco');
      expect(content.text).toContain('✅');
    });

    it('should upload video with mp4 extension', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      const existingChannel = { id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([
        existingCategory,
        existingChannel,
      ]);
      mockDownload.mockResolvedValue(Buffer.from('vid-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasVideoMessage: true } },
      );

      await command.run(data);

      expect(mockDiscord.uploadMedia).toHaveBeenCalledWith(
        'ch-1',
        expect.any(Buffer),
        expect.stringMatching(/^video_\d+\.mp4$/),
      );
    });

    it('should upload audio with ogg extension', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      const existingChannel = { id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([
        existingCategory,
        existingChannel,
      ]);
      mockDownload.mockResolvedValue(Buffer.from('aud-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasAudioMessage: true } },
      );

      await command.run(data);

      expect(mockDiscord.uploadMedia).toHaveBeenCalledWith(
        'ch-1',
        expect.any(Buffer),
        expect.stringMatching(/^audio_\d+\.ogg$/),
      );
    });

    it('should extract media from quoted message', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      const existingChannel = { id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([
        existingCategory,
        existingChannel,
      ]);
      mockDownload.mockResolvedValue(Buffer.from('img-data'));

      const data = GroupCommandData.build({ text: ',drive 2026 churrasco' });
      // Manually set quoted image
      data.message = {
        extendedTextMessage: {
          text: ',drive 2026 churrasco',
          contextInfo: {
            quotedMessage: {
              imageMessage: {
                url: 'https://example.com/quoted.jpg',
                mimetype: 'image/jpeg',
              },
            },
          },
        },
      };

      const messages = await command.run(data);

      expect(mockDiscord.uploadMedia).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('✅');
    });

    it('should pass reuploadRequest to downloadMediaMessage', async () => {
      const existingCategory = { id: 'cat-1', name: '2026', type: 4 };
      const existingChannel = { id: 'ch-1', name: 'churrasco', type: 0, parent_id: 'cat-1' };
      (mockDiscord.getChannels as ReturnType<typeof vi.fn>).mockResolvedValue([
        existingCategory,
        existingChannel,
      ]);
      mockDownload.mockResolvedValue(Buffer.from('img-data'));

      const data = GroupCommandData.build(
        { text: ',drive 2026 churrasco' },
        { transient: { hasImageMessage: true } },
      );

      await command.run(data);

      expect(mockDownload).toHaveBeenCalledWith(
        expect.anything(),
        'buffer',
        {},
        expect.objectContaining({ reuploadRequest: mockWhatsApp.updateMediaMessage }),
      );
    });
  });
});
