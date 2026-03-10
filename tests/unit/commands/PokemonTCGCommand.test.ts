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

const mockCard = {
  name: 'Charizard',
  supertype: 'Pokémon',
  subtypes: ['Stage 2'],
  hp: '150',
  types: ['Fire'],
  rarity: 'Rare Holo',
  artist: 'Mitsuhiro Arita',
  flavorText: 'Spits fire that is hot enough to melt boulders.',
  number: '4',
  images: {
    small: 'https://images.pokemontcg.io/base1/4.png',
    large: 'https://images.pokemontcg.io/base1/4_hires.png',
  },
  set: { name: 'Base Set', printedTotal: 102 },
};

const mockCountResponse = { data: { data: [], totalCount: 20000 } };
const mockCardResponse = { data: { data: [mockCard], totalCount: 20000 } };

describe('PokemonTCGCommand', () => {
  let command: PokemonTCGCommand;

  beforeEach(() => {
    command = new PokemonTCGCommand();
    vi.clearAllMocks();
    delete process.env.POKEMON_TCG_API_KEY;
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
    it('should perform 2-step pagination and return card image', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',pokemontcg' });
      const messages = await command.run(data);

      expect(mockGet).toHaveBeenCalledTimes(2);
      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe(mockCard.images.large);
    });

    it('should include card metadata in caption', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);

      const data = GroupCommandData.build({ text: ',pokemontcg' });
      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*Charizard*');
      expect(content.caption).toContain('Pokémon');
      expect(content.caption).toContain('Stage 2');
      expect(content.caption).toContain('HP: 150');
      expect(content.caption).toContain('🔥');
      expect(content.caption).toContain('Base Set');
      expect(content.caption).toContain('#4/102');
      expect(content.caption).toContain('Rare Holo');
      expect(content.caption).toContain('Mitsuhiro Arita');
      expect(content.caption).toContain('Spits fire that is hot enough to melt boulders.');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',pokemontcg dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should include X-Api-Key header when POKEMON_TCG_API_KEY is set', async () => {
      process.env.POKEMON_TCG_API_KEY = 'test-api-key';
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ headers: { 'X-Api-Key': 'test-api-key' } }),
      );
    });

    it('should not include headers when POKEMON_TCG_API_KEY is not set', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.not.objectContaining({ headers: expect.anything() }),
      );
    });

    it('should always pass timeout in request config', async () => {
      mockGet.mockResolvedValueOnce(mockCountResponse).mockResolvedValueOnce(mockCardResponse);
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ timeout: 60000 }),
      );
    });

    it('should return error text when API throws', async () => {
      mockGet.mockRejectedValueOnce(new Error('timeout of 60000ms exceeded'));
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível buscar');
    });

    it('should return fallback text when card has no image', async () => {
      const cardWithoutImage = { ...mockCard, images: { small: '', large: '' } };
      mockGet
        .mockResolvedValueOnce(mockCountResponse)
        .mockResolvedValueOnce({ data: { data: [cardWithoutImage], totalCount: 20000 } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não foi possível encontrar');
    });

    it('should handle card without optional fields', async () => {
      const minimalCard = {
        name: 'Energy',
        supertype: 'Energy',
        number: '1',
        images: { small: 'https://example.com/s.png', large: 'https://example.com/l.png' },
        set: { name: 'Base Set', printedTotal: 102 },
      };
      mockGet
        .mockResolvedValueOnce(mockCountResponse)
        .mockResolvedValueOnce({ data: { data: [minimalCard], totalCount: 20000 } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokemontcg' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe(minimalCard.images.large);
    });
  });
});
