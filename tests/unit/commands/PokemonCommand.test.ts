import { describe, it, expect, beforeEach, vi } from 'vitest';
import PokemonCommand from '../../../src/commands/PokemonCommand.js';
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

const mockPokemon = {
  name: 'pikachu',
  id: 25,
  types: [{ type: { name: 'electric' } }],
  sprites: {
    front_default:
      'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png',
    other: {
      'official-artwork': {
        front_default:
          'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png',
      },
    },
  },
};

const mockPokemonNoArtwork = {
  ...mockPokemon,
  name: 'missingno',
  sprites: {
    front_default: 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/0.png',
    other: { 'official-artwork': { front_default: null } },
  },
};

describe('PokemonCommand', () => {
  let command: PokemonCommand;

  beforeEach(() => {
    command = new PokemonCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', pokémon', true],
      [',pokémon', true],
      [', pokemon', true],
      [', POKÉMON', true],
      [', pokémon team', true],
      [', pokémon show', true],
      [', pokémon dm', true],
      ['  , pokémon  ', true],
      ['pokémon', false],
      ['hello', false],
      [', pokémon extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run() - single pokemon', () => {
    it('should return pokemon with type emojis and official artwork', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0.024);
      const data = GroupCommandData.build({ text: ',pokémon' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { caption: string; image: { url: string } };
      expect(content.caption).toContain('Pikachu');
      expect(content.caption).toContain('⚡');
      expect(content.caption).toContain('#25');
      expect(content.image.url).toContain('official-artwork');
    });

    it('should fallback to front_default when official artwork is null', async () => {
      mockGet.mockResolvedValue({ data: mockPokemonNoArtwork });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon' });

      const messages = await command.run(data);

      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe(mockPokemonNoArtwork.sprites.front_default);
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',pokémon dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });
  });

  describe('run() - team mode', () => {
    it('should return team of 6 pokemon with grid image', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
      vi.spyOn(Math, 'random').mockReturnValue(0.024);
      const data = GroupCommandData.build({ text: ',pokémon team' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(mockGet).toHaveBeenCalledTimes(6);
      expect(mockGetBuffer).toHaveBeenCalledTimes(6);
      const content = messages[0].content as { caption: string; image: Buffer };
      expect(content.caption).toContain('*1.*');
      expect(content.caption).toContain('Pikachu');
      expect(Buffer.isBuffer(content.image)).toBe(true);
    });

    it('should set viewOnce to true by default for team', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon team' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: mockPokemon });
      mockGetBuffer.mockResolvedValue(Buffer.from('mock-image'));
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',pokémon team', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
