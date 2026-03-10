import { describe, it, expect, beforeEach, vi } from 'vitest';
import PokemonTCGCommand from '../../../src/commands/PokemonTCGCommand.js';
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
const mockImageBuffer = Buffer.from('fake-image-data');

const mockCard = {
  id: 'base1-4',
  localId: '4',
  name: 'Charizard',
  category: 'Pokemon',
  image: 'https://assets.tcgdex.net/en/base/base1/4',
  illustrator: 'Mitsuhiro Arita',
  rarity: 'Rare',
  hp: 120,
  types: ['Fire'],
  stage: 'Stage2',
  set: {
    name: 'Base Set',
    cardCount: { total: 102, official: 102 },
  },
};

const mockCardResponse = { data: mockCard };

describe('PokemonTCGCommand', () => {
  let command: PokemonTCGCommand;

  beforeEach(() => {
    command = new PokemonTCGCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',pokemontcg', true],
      [', pokemontcg', true],
      [', POKEMONTCG', true],
      [', pokémontcg', true],
      [', pokemontcg show', true],
      [', pokemontcg dm', true],
      [',ptcg', true],
      [', ptcg', true],
      [', ptcg show', true],
      ['pokemontcg', false],
      ['hello', false],
      [', pokemontcg extra', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should fetch random card and return image buffer', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(1);
      expect(mockGet).toHaveBeenCalledWith(
        'https://api.tcgdex.net/v2/en/random/card',
        expect.objectContaining({ timeout: 30000, retries: 0 }),
      );
      expect(mockGetBuffer).toHaveBeenCalledWith(
        `${mockCard.image}/high.webp`,
        expect.objectContaining({ timeout: 30000 }),
      );
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: Buffer };
      expect(content.image).toBe(mockImageBuffer);
    });

    it('should include card metadata in caption', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*Charizard*');
      expect(content.caption).toContain('Pokemon');
      expect(content.caption).toContain('Stage2');
      expect(content.caption).toContain('HP: 120');
      expect(content.caption).toContain('🔥');
      expect(content.caption).toContain('Base Set');
      expect(content.caption).toContain('#4/102');
      expect(content.caption).toContain('Rare');
      expect(content.caption).toContain('Mitsuhiro Arita');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = PrivateCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should return error text when API throws', async () => {
      mockGet.mockRejectedValueOnce(new Error('timeout of 30000ms exceeded'));
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível buscar');
    });

    it('should return error text when image download fails', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockRejectedValueOnce(new Error('Request failed with status code 404'));
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível buscar');
    });

    it('should retry up to 3 times when card has no image', async () => {
      const cardNoImage = { ...mockCard, image: undefined };
      mockGet.mockResolvedValueOnce({ data: cardNoImage }).mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(2);
      const content = messages[0].content as { image: Buffer };
      expect(content.image).toBe(mockImageBuffer);
    });

    it('should return fallback and report to Sentry when all retries have no image', async () => {
      const cardNoImage = { ...mockCard, image: undefined };
      mockGet
        .mockResolvedValueOnce({ data: cardNoImage })
        .mockResolvedValueOnce({ data: cardNoImage })
        .mockResolvedValueOnce({ data: cardNoImage });
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(3);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível encontrar');
      expect(Sentry.captureMessage).toHaveBeenCalledWith(
        'PokemonTCG: no card with image after retries',
        'warning',
      );
    });

    it('should handle card without optional fields', async () => {
      const minimalCard = {
        id: 'base1-99',
        localId: '99',
        name: 'Energy',
        category: 'Energy',
        image: 'https://assets.tcgdex.net/en/base/base1/99',
        set: {
          name: 'Base Set',
          cardCount: { total: 102, official: 102 },
        },
      };
      mockGet.mockResolvedValueOnce({ data: minimalCard });
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(mockGetBuffer).toHaveBeenCalledWith(
        `${minimalCard.image}/high.webp`,
        expect.any(Object),
      );
      const content = messages[0].content as { image: Buffer };
      expect(content.image).toBe(mockImageBuffer);
    });

    describe('regression: image format, retries, and timeouts', () => {
      it('should download image as webp, not png', async () => {
        mockGet.mockResolvedValueOnce(mockCardResponse);
        mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
        const data = GroupCommandData.build({ text: ',pokemontcg' });

        await command.run(data);

        const imageUrl = mockGetBuffer.mock.calls[0][0] as string;
        expect(imageUrl).toMatch(/\.webp$/);
        expect(imageUrl).not.toMatch(/\.png$/);
      });

      it('should disable retries on API call to avoid hidden latency', async () => {
        mockGet.mockResolvedValueOnce(mockCardResponse);
        mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
        const data = GroupCommandData.build({ text: ',pokemontcg' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ retries: 0 }),
        );
      });

      it('should disable retries on image download to avoid hidden latency', async () => {
        mockGet.mockResolvedValueOnce(mockCardResponse);
        mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
        const data = GroupCommandData.build({ text: ',pokemontcg' });

        await command.run(data);

        expect(mockGetBuffer).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ retries: 0 }),
        );
      });

      it('should set timeout on both API call and image download', async () => {
        mockGet.mockResolvedValueOnce(mockCardResponse);
        mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
        const data = GroupCommandData.build({ text: ',pokemontcg' });

        await command.run(data);

        expect(mockGet).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ timeout: expect.any(Number) }),
        );
        expect(mockGetBuffer).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({ timeout: expect.any(Number) }),
        );
      });

      it('should pre-download image as buffer instead of passing URL', async () => {
        mockGet.mockResolvedValueOnce(mockCardResponse);
        mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
        const data = GroupCommandData.build({ text: ',pokemontcg' });

        const messages = await command.run(data);

        expect(mockGetBuffer).toHaveBeenCalledTimes(1);
        const content = messages[0].content as { image: Buffer };
        expect(Buffer.isBuffer(content.image)).toBe(true);
        expect(content.image).not.toEqual(expect.objectContaining({ url: expect.any(String) }));
      });
    });

    it('should not include headers (no API key needed)', async () => {
      mockGet.mockResolvedValueOnce(mockCardResponse);
      mockGetBuffer.mockResolvedValueOnce(mockImageBuffer);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.not.objectContaining({ headers: expect.anything() }),
      );
    });
  });
});
