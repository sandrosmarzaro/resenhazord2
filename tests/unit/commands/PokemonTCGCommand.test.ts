import { describe, it, expect, beforeEach, vi } from 'vitest';
import PokemonTCGCommand from '../../../src/commands/PokemonTCGCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockSets = [
  { id: 'base1', name: 'Base Set', cardCount: { total: 102, official: 102 } },
  { id: 'swsh1', name: 'Sword & Shield', cardCount: { total: 216, official: 202 } },
];

const mockSetDetail = {
  id: 'base1',
  name: 'Base Set',
  cardCount: { total: 102, official: 102 },
  cards: [
    {
      id: 'base1-4',
      localId: '4',
      name: 'Charizard',
      image: 'https://assets.tcgdex.net/en/base/base1/4',
    },
    { id: 'base1-100', localId: '100', name: 'Energy' },
  ],
};

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

const mockSetsResponse = { data: mockSets };
const mockSetDetailResponse = { data: mockSetDetail };
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
    it('should perform 3-step fetch and return card image', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',pokemontcg' });
      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(3);
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe(`${mockCard.image}/high.png`);
    });

    it('should call correct TCGdex endpoints', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',pokemontcg' });
      await command.run(data);

      expect(mockGet).toHaveBeenNthCalledWith(
        1,
        'https://api.tcgdex.net/v2/en/sets',
        expect.objectContaining({ timeout: 15000 }),
      );
      expect(mockGet).toHaveBeenNthCalledWith(
        2,
        'https://api.tcgdex.net/v2/en/sets/base1',
        expect.objectContaining({ timeout: 15000 }),
      );
      expect(mockGet).toHaveBeenNthCalledWith(
        3,
        'https://api.tcgdex.net/v2/en/cards/base1-4',
        expect.objectContaining({ timeout: 15000 }),
      );
    });

    it('should skip cards without images when picking from set', async () => {
      const setWithMixedCards = {
        ...mockSetDetail,
        cards: [
          { id: 'base1-100', localId: '100', name: 'Energy' },
          {
            id: 'base1-4',
            localId: '4',
            name: 'Charizard',
            image: 'https://assets.tcgdex.net/en/base/base1/4',
          },
        ],
      };
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce({ data: setWithMixedCards })
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',pokemontcg' });
      const messages = await command.run(data);

      expect(mockGet).toHaveBeenNthCalledWith(
        3,
        'https://api.tcgdex.net/v2/en/cards/base1-4',
        expect.any(Object),
      );
      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe(`${mockCard.image}/high.png`);
    });

    it('should include card metadata in caption', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

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
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should always pass timeout in request config', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ timeout: 15000 }),
      );
    });

    it('should return error text when API throws', async () => {
      mockGet.mockRejectedValueOnce(new Error('timeout of 15000ms exceeded'));
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível buscar');
    });

    it('should return fallback text when set has no cards with images', async () => {
      const setNoImages = {
        ...mockSetDetail,
        cards: [{ id: 'base1-100', localId: '100', name: 'Energy' }],
      };
      mockGet.mockResolvedValueOnce(mockSetsResponse).mockResolvedValueOnce({ data: setNoImages });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível encontrar');
    });

    it('should return fallback text when card detail has no image', async () => {
      const cardNoImage = { ...mockCard, image: undefined };
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce({ data: cardNoImage });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível encontrar');
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
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce({ data: minimalCard });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe(`${minimalCard.image}/high.png`);
    });

    it('should not include headers (no API key needed)', async () => {
      mockGet
        .mockResolvedValueOnce(mockSetsResponse)
        .mockResolvedValueOnce(mockSetDetailResponse)
        .mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.not.objectContaining({ headers: expect.anything() }),
      );
    });
  });
});
