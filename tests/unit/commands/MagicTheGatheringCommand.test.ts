import { describe, it, expect, beforeEach, vi } from 'vitest';
import MagicTheGatheringCommand from '../../../src/commands/MagicTheGatheringCommand.js';
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
  name: 'Lightning Bolt',
  text: 'Lightning Bolt deals 3 damage to any target.',
  imageUrl: 'https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid=234704',
};

const mockFetch = vi.fn();

describe('MagicTheGatheringCommand', () => {
  let command: MagicTheGatheringCommand;

  beforeEach(() => {
    command = new MagicTheGatheringCommand();
    vi.clearAllMocks();
    // Mock fetch HEAD requests — return the card's own URL (not a card_back redirect)
    mockFetch.mockResolvedValue({ url: mockCard.imageUrl });
    vi.stubGlobal('fetch', mockFetch);
  });

  describe('matches()', () => {
    it.each([
      [', mtg', true],
      [',mtg', true],
      [', MTG', true],
      [', mtg show', true],
      [', mtg dm', true],
      [', mtg booster', true],
      ['  , mtg  ', true],
      ['mtg', false],
      ['hello', false],
      [', mtg extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should perform 2-step pagination and return card', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '500' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',mtg' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(2);
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe(mockCard.imageUrl);
      expect(content.caption).toContain('*Lightning Bolt*');
      expect(content.caption).toContain('Lightning Bolt deals 3 damage');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',mtg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should skip cards whose image redirects to card_back and retry', async () => {
      mockGet
        .mockResolvedValueOnce({ headers: { 'total-count': '100' }, data: {} })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      // First attempt resolves to card_back, second resolves to real image
      mockFetch
        .mockResolvedValueOnce({ url: 'https://gatherer.wizards.com/assets/card_back.webp' })
        .mockResolvedValueOnce({ url: mockCard.imageUrl });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',mtg' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(3); // 1 total + 2 page fetches
      expect(messages[0].content).toMatchObject({ image: { url: mockCard.imageUrl } });
    });

    describe('booster mode', () => {
      it('should return a grid of 6 cards with numbered caption', async () => {
        mockGet
          .mockResolvedValueOnce({ headers: { 'total-count': '600' }, data: {} })
          .mockResolvedValue({ data: { cards: [mockCard] } });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        vi.spyOn(Math, 'random').mockReturnValue(0);
        const data = GroupCommandData.build({ text: ',mtg booster' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        expect(mockGet).toHaveBeenCalledTimes(7); // 1 total-count + 6 page fetches
        expect(mockGetBuffer).toHaveBeenCalledTimes(6);
        const content = messages[0].content as { caption: string; image: Buffer };
        expect(content.caption).toContain('*1.*');
        expect(content.caption).toContain('Lightning Bolt');
        expect(Buffer.isBuffer(content.image)).toBe(true);
      });

      it('should set viewOnce to true by default for booster', async () => {
        mockGet
          .mockResolvedValueOnce({ headers: { 'total-count': '600' }, data: {} })
          .mockResolvedValue({ data: { cards: [mockCard] } });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        vi.spyOn(Math, 'random').mockReturnValue(0);
        const data = GroupCommandData.build({ text: ',mtg booster' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(true);
      });

      it('should set viewOnce to false with show flag for booster', async () => {
        mockGet
          .mockResolvedValueOnce({ headers: { 'total-count': '600' }, data: {} })
          .mockResolvedValue({ data: { cards: [mockCard] } });
        mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
        vi.spyOn(Math, 'random').mockReturnValue(0);
        const data = GroupCommandData.build({ text: ',mtg booster show' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(false);
      });
    });
  });
});
