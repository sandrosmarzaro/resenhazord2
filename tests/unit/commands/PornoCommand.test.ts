import { describe, it, expect, beforeEach, vi } from 'vitest';
import PornoCommand from '../../../src/commands/PornoCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

vi.mock('../../../src/services/XVideosScraper.js', () => ({
  default: {
    getRandomVideo: vi.fn().mockResolvedValue({
      videoUrl: 'https://example.com/video.mp4',
      title: 'Test Video',
    }),
  },
}));

import XVideosScraper from '../../../src/services/XVideosScraper.js';

const mockGetRandomVideo = XVideosScraper.getRandomVideo as ReturnType<typeof vi.fn>;

describe('PornoCommand', () => {
  let command: PornoCommand;

  beforeEach(() => {
    command = new PornoCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', porno', true],
      [',porno', true],
      [', PORNO', true],
      [', porno ia', true],
      [', porno show', true],
      [', porno dm', true],
      ['  , porno  ', true],
      ['porno', false],
      ['hello', false],
      [', porno extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run() - ia mode', () => {
    it('should return NSFW content from nsfwhub', async () => {
      const data = GroupCommandData.build({ text: ',porno ia' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as Record<string, unknown>;
      expect(content.caption).toBeDefined();
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ',porno ia' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ',porno ia show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ',porno ia dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });
  });

  describe('run() - real mode', () => {
    it('should return video from XVideosScraper', async () => {
      const data = GroupCommandData.build({ text: ',porno' });

      const messages = await command.run(data);

      expect(mockGetRandomVideo).toHaveBeenCalled();
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { video: { url: string }; caption: string };
      expect(content.video.url).toBe('https://example.com/video.mp4');
      expect(content.caption).toBe('Test Video');
    });

    it('should return error message when scraper fails', async () => {
      mockGetRandomVideo.mockRejectedValueOnce(new Error('Scrape Error'));
      const data = GroupCommandData.build({ text: ',porno' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não consegui baixar');
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ',porno' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ',porno show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ',porno dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ',porno dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ',porno' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ',porno', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
