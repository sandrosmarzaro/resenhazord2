import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import AnimalCommand from '../../../src/commands/AnimalCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';
import { Sentry } from '../../../src/infra/Sentry.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
    getBuffer: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;
const mockGetBuffer = AxiosClient.getBuffer as ReturnType<typeof vi.fn>;

const mockWikipediaResponse = {
  extract:
    'The giant panda is a bear species endemic to China. It is characterised by its black-and-white coat.',
  thumbnail: { source: 'https://upload.wikimedia.org/wikipedia/commons/thumb/panda.jpg' },
};

describe('AnimalCommand', () => {
  let command: AnimalCommand;

  beforeEach(() => {
    command = new AnimalCommand();
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: mockWikipediaResponse });
    mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
  });

  describe('matches()', () => {
    it.each([
      [',animal', true],
      [', animal', true],
      [', ANIMAL', true],
      [', animal show', true],
      [', animal dm', true],
      ['animal', false],
      ['hello', false],
      [', animal extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return 1 message with image buffer', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: Buffer };
      expect(Buffer.isBuffer(content.image)).toBe(true);
    });

    it('should include animal name and fact in caption', async () => {
      vi.spyOn(Math, 'random').mockReturnValue(0.3); // picks panda (index 6 of 20)
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🐼 Panda');
      expect(content.caption).toContain('📝');
      expect(content.caption).toContain('giant panda is a bear species');
    });

    it('should format red_panda as "Red Panda"', async () => {
      vi.spyOn(Math, 'random').mockReturnValue(0.42); // picks red_panda (index 8 of 20)
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Red Panda');
    });

    it('should call Wikipedia API with User-Agent and retries: 0', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.stringMatching(/^https:\/\/en\.wikipedia\.org\/api\/rest_v1\/page\/summary\//),
        { retries: 0, timeout: 10000, headers: { 'User-Agent': 'ResenhazordBot/2.0' } },
      );
    });

    it('should pass User-Agent header when downloading thumbnail', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      await command.run(data);

      expect(mockGetBuffer).toHaveBeenCalledWith(mockWikipediaResponse.thumbnail.source, {
        headers: { 'User-Agent': 'ResenhazordBot/2.0' },
      });
    });

    it('should return text-only reply when thumbnail is missing', async () => {
      mockGet.mockResolvedValue({
        data: { extract: 'Some fact about the animal.', thumbnail: undefined },
      });
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('📝');
      expect(mockGetBuffer).not.toHaveBeenCalled();
    });

    it('should extract first two sentences as fact', async () => {
      mockGet.mockResolvedValue({
        data: {
          extract: 'First sentence. Second sentence. Third sentence.',
          thumbnail: { source: 'https://example.com/img.jpg' },
        },
      });
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('First sentence. Second sentence.');
      expect(content.caption).not.toContain('Third sentence.');
    });

    it('should use only first sentence when two sentences exceed 300 chars', async () => {
      const longSecond = 'B'.repeat(300);
      mockGet.mockResolvedValue({
        data: {
          extract: `Short. ${longSecond}.`,
          thumbnail: { source: 'https://example.com/img.jpg' },
        },
      });
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Short.');
      expect(content.caption).not.toContain(longSecond);
    });

    describe('on 429 rate limit', () => {
      beforeEach(() => vi.useFakeTimers());
      afterEach(() => vi.useRealTimers());

      it('should wait retry-after seconds and retry, returning image on success', async () => {
        const rateLimitError = Object.assign(new Error('Too Many Requests'), {
          isAxiosError: true,
          response: { status: 429, headers: { 'retry-after': '60' } },
        });
        mockGet
          .mockRejectedValueOnce(rateLimitError)
          .mockResolvedValueOnce({ data: mockWikipediaResponse });
        const data = GroupCommandData.build({ text: ',animal' });

        const runPromise = command.run(data);
        await vi.runAllTimersAsync();
        const messages = await runPromise;

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
        expect(mockGet).toHaveBeenCalledTimes(2);
        expect(Sentry.captureException).not.toHaveBeenCalled();
      });

      it('should default to 60s wait when retry-after header is missing', async () => {
        const rateLimitError = Object.assign(new Error('Too Many Requests'), {
          isAxiosError: true,
          response: { status: 429, headers: {} },
        });
        mockGet
          .mockRejectedValueOnce(rateLimitError)
          .mockResolvedValueOnce({ data: mockWikipediaResponse });
        const data = GroupCommandData.build({ text: ',animal' });

        const runPromise = command.run(data);
        await vi.advanceTimersByTimeAsync(59_999);
        expect(mockGet).toHaveBeenCalledTimes(1);
        await vi.advanceTimersByTimeAsync(1);
        const messages = await runPromise;

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
        expect(mockGet).toHaveBeenCalledTimes(2);
      });

      it('should return no messages silently if all retries hit 429', async () => {
        const rateLimitError = Object.assign(new Error('Too Many Requests'), {
          isAxiosError: true,
          response: { status: 429, headers: { 'retry-after': '30' } },
        });
        mockGet.mockRejectedValue(rateLimitError);
        const data = GroupCommandData.build({ text: ',animal' });

        const runPromise = command.run(data);
        await vi.runAllTimersAsync();
        const messages = await runPromise;

        expect(messages).toHaveLength(0);
        expect(mockGet).toHaveBeenCalledTimes(4);
        expect(Sentry.captureException).not.toHaveBeenCalled();
      });
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ',animal show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ',animal dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ',animal dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ',animal', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should return error text on API failure', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toBeTruthy();
    });
  });
});
