import { describe, it, expect, beforeEach, vi } from 'vitest';
import DownloadCommand from '../../../src/commands/DownloadCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

vi.mock('../../../src/services/YtDlpService.js', () => ({
  default: {
    download: vi.fn().mockResolvedValue({
      buffer: Buffer.from('video-data'),
      title: 'Test Video',
    }),
  },
}));

import YtDlpService from '../../../src/services/YtDlpService.js';

const mockDownload = YtDlpService.download as ReturnType<typeof vi.fn>;

describe('DownloadCommand', () => {
  let command: DownloadCommand;

  beforeEach(() => {
    command = new DownloadCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',dl https://x.com/user/status/123', true],
      [', dl https://x.com/user/status/123', true],
      [',baixar https://instagram.com/reel/abc', true],
      [', baixar https://youtube.com/shorts/abc', true],
      [',DL https://x.com/foo', true],
      [',dl', false],
      [',dl not-a-url', false],
      ['dl https://x.com', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run() - success', () => {
    it('should return 1 message with video buffer', async () => {
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123' });

      const messages = await command.run(data);

      expect(mockDownload).toHaveBeenCalledWith('https://x.com/user/status/123');
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { video: Buffer; caption: string };
      expect(content.video).toBeInstanceOf(Buffer);
      expect(content.caption).toBe('Test Video');
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123 show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123 dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ',dl https://x.com/user/status/123 dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({
        text: ',dl https://x.com/user/status/123',
        expiration: 86400,
      });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should work with baixar alias', async () => {
      const data = GroupCommandData.build({ text: ',baixar https://instagram.com/reel/abc' });

      const messages = await command.run(data);

      expect(mockDownload).toHaveBeenCalledWith('https://instagram.com/reel/abc');
      expect(messages).toHaveLength(1);
    });
  });

  describe('run() - error', () => {
    it('should return error text message when yt-dlp fails', async () => {
      mockDownload.mockRejectedValueOnce(new Error('yt-dlp exited with code 1'));
      const data = GroupCommandData.build({ text: ',dl https://x.com/user/status/123' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não consegui baixar');
    });
  });
});
