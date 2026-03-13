import { describe, it, expect, beforeEach, vi } from 'vitest';
import YugiohCommand from '../../../src/commands/YugiohCommand.js';
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

const mockCard = {
  data: [
    {
      name: 'Dark Magician',
      desc: 'The ultimate wizard\nin terms of attack\nand defense.',
      card_images: [{ image_url: 'https://images.ygoprodeck.com/images/cards/46986414.jpg' }],
    },
  ],
};

describe('YugiohCommand', () => {
  let command: YugiohCommand;

  beforeEach(() => {
    command = new YugiohCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', ygo', true],
      [',ygo', true],
      [', YGO', true],
      [', ygo show', true],
      [', ygo dm', true],
      [', ygo booster', true],
      ['  , ygo  ', true],
      ['ygo', false],
      ['hello', false],
      [', ygo extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return image with card data', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe('https://images.ygoprodeck.com/images/cards/46986414.jpg');
      expect(content.caption).toContain('*Dark Magician*');
    });

    it('should strip newlines from description', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).not.toContain('\n> The ultimate wizard\n');
      expect(content.caption).toContain('The ultimate wizardin terms of attackand defense.');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = PrivateCommandData.build({ text: ',ygo dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: mockCard });
      const data = GroupCommandData.build({ text: ',ygo', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    describe('booster mode', () => {
      it('should return a grid of 6 cards with numbered caption', async () => {
        mockGet.mockResolvedValue({ data: mockCard });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        const data = GroupCommandData.build({ text: ',ygo booster' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        expect(mockGet).toHaveBeenCalledTimes(6);
        expect(mockGetBuffer).toHaveBeenCalledTimes(6);
        const content = messages[0].content as { caption: string; image: Buffer };
        expect(content.caption).toContain('*1.*');
        expect(content.caption).toContain('Dark Magician');
        expect(Buffer.isBuffer(content.image)).toBe(true);
      });

      it('should set viewOnce to true by default for booster', async () => {
        mockGet.mockResolvedValue({ data: mockCard });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        const data = GroupCommandData.build({ text: ',ygo booster' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(true);
      });

      it('should set viewOnce to false with show flag for booster', async () => {
        mockGet.mockResolvedValue({ data: mockCard });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        const data = GroupCommandData.build({ text: ',ygo booster show' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(false);
      });
    });
  });
});
