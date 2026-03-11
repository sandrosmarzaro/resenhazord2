import { describe, it, expect, beforeEach, vi } from 'vitest';
import AnimalCommand from '../../../src/commands/AnimalCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
    getBuffer: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;
const mockGetBuffer = AxiosClient.getBuffer as ReturnType<typeof vi.fn>;

const mockAnimalResponse = {
  image: 'https://cdn.some-random-api.com/img/panda/panda1.jpg',
  fact: 'Pandas spend around 10-16 hours a day eating bamboo.',
};

describe('AnimalCommand', () => {
  let command: AnimalCommand;

  beforeEach(() => {
    command = new AnimalCommand();
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ data: mockAnimalResponse });
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
      vi.spyOn(Math, 'random').mockReturnValue(0.6); // picks panda (index 6)
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🐼 Panda');
      expect(content.caption).toContain('📝');
      expect(content.caption).toContain(mockAnimalResponse.fact);
    });

    it('should format red_panda as "Red Panda"', async () => {
      vi.spyOn(Math, 'random').mockReturnValue(0.85); // picks red_panda (index 8)
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Red Panda');
    });

    it('should call API with retries: 0 and timeout: 10000', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.stringMatching(/^https:\/\/some-random-api\.com\/animal\//),
        { retries: 0, timeout: 10000 },
      );
    });

    it('should pre-download image as buffer', async () => {
      const data = GroupCommandData.build({ text: ',animal' });

      await command.run(data);

      expect(mockGetBuffer).toHaveBeenCalledWith(mockAnimalResponse.image);
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

    it('should return rate limit message without capturing to Sentry on 429', async () => {
      const rateLimitError = Object.assign(new Error('Too Many Requests'), {
        isAxiosError: true,
        response: { status: 429 },
      });
      mockGet.mockRejectedValue(rateLimitError);
      const data = GroupCommandData.build({ text: ',animal' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('1 minuto');
    });
  });
});
