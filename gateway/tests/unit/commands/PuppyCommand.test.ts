import { describe, it, expect, beforeEach, vi } from 'vitest';
import PuppyCommand from '../../../src/commands/PuppyCommand.js';
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

const mockDogResponse = {
  message: 'https://images.dog.ceo/breeds/beagle/n02088364_1.jpg',
  status: 'success',
};

const mockCatResponse = {
  id: 'abc123',
  url: 'https://cataas.com/cat/abc123',
  tags: [],
};

describe('PuppyCommand', () => {
  let command: PuppyCommand;

  beforeEach(() => {
    command = new PuppyCommand();
    vi.clearAllMocks();
    mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
  });

  describe('matches()', () => {
    it.each([
      [',puppy', true],
      [', puppy', true],
      [', PUPPY', true],
      [', puppy dog', true],
      [', puppy cat', true],
      [', puppy show', true],
      [', puppy dm', true],
      ['puppy', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    describe('dog option', () => {
      beforeEach(() => {
        mockGet.mockResolvedValue({ data: mockDogResponse });
      });

      it('should call Dog CEO API when tipo=dog', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith('https://dog.ceo/api/breeds/image/random', {
          retries: 0,
          timeout: 10000,
        });
      });

      it('should include breed in caption for dog', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('🐶 Beagle');
      });

      it('should return image buffer for dog', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
      });
    });

    describe('cat option', () => {
      beforeEach(() => {
        mockGet.mockResolvedValue({ data: mockCatResponse });
      });

      it('should call Cataas API when tipo=cat', async () => {
        const data = GroupCommandData.build({ text: ',puppy cat' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith('https://cataas.com/cat?json=true', {
          retries: 0,
          timeout: 10000,
        });
      });

      it('should include cat caption', async () => {
        const data = GroupCommandData.build({ text: ',puppy cat' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('🐱 Cat');
      });

      it('should construct full Cataas image URL', async () => {
        const data = GroupCommandData.build({ text: ',puppy cat' });

        await command.run(data);

        expect(mockGetBuffer).toHaveBeenCalledWith(mockCatResponse.url, {
          headers: { Accept: '*/*' },
        });
      });
    });

    describe('random selection', () => {
      it('should fetch dog when Math.random() < 0.5', async () => {
        mockGet.mockResolvedValue({ data: mockDogResponse });
        vi.spyOn(Math, 'random').mockReturnValue(0.3);
        const data = GroupCommandData.build({ text: ',puppy' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith(
          'https://dog.ceo/api/breeds/image/random',
          expect.any(Object),
        );
      });

      it('should fetch cat when Math.random() >= 0.5', async () => {
        mockGet.mockResolvedValue({ data: mockCatResponse });
        vi.spyOn(Math, 'random').mockReturnValue(0.7);
        const data = GroupCommandData.build({ text: ',puppy' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith(
          'https://cataas.com/cat?json=true',
          expect.any(Object),
        );
      });
    });

    describe('breed extraction', () => {
      it('should format hyphenated breed as title case', async () => {
        mockGet.mockResolvedValue({
          data: {
            message: 'https://images.dog.ceo/breeds/terrier-scottish/n0012345.jpg',
            status: 'success',
          },
        });
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('🐶 Terrier Scottish');
      });

      it('should fall back to "Dog" when breed cannot be extracted', async () => {
        mockGet.mockResolvedValue({
          data: { message: 'https://images.dog.ceo/no-breed-path.jpg', status: 'success' },
        });
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('🐶 Dog');
      });
    });

    describe('message flags', () => {
      beforeEach(() => {
        mockGet.mockResolvedValue({ data: mockDogResponse });
      });

      it('should set viewOnce to true by default', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(true);
      });

      it('should set viewOnce to false with show flag', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog show' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(false);
      });

      it('should send to DM when dm flag is active in group', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.participant);
      });

      it('should not change jid when dm flag is active in private chat', async () => {
        const data = PrivateCommandData.build({ text: ',puppy dog dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.remoteJid);
      });

      it('should quote the original message', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        expect(messages[0].options?.quoted).toBe(data);
      });

      it('should include ephemeral expiration from data', async () => {
        const data = GroupCommandData.build({ text: ',puppy dog', expiration: 86400 });

        const messages = await command.run(data);

        expect(messages[0].options?.ephemeralExpiration).toBe(86400);
      });
    });

    describe('error handling', () => {
      it('should return error text on API failure', async () => {
        mockGet.mockRejectedValue(new Error('Network error'));
        const data = GroupCommandData.build({ text: ',puppy dog' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Erro ao buscar imagem');
      });

      it('should call Sentry.captureException on error', async () => {
        const error = new Error('Network error');
        mockGet.mockRejectedValue(error);
        const data = GroupCommandData.build({ text: ',puppy dog' });

        await command.run(data);

        expect(Sentry.captureException).toHaveBeenCalledWith(error, {
          extra: { command: 'puppy' },
        });
      });
    });
  });
});
