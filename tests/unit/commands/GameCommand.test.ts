import { describe, it, expect, beforeEach, vi } from 'vitest';
import GameCommand from '../../../src/commands/GameCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';
import IgdbService from '../../../src/services/IgdbService.js';

const mockRawgGame = {
  name: 'The Legend of Zelda: Ocarina of Time',
  released: '1998-11-21',
  background_image: 'https://media.rawg.io/media/games/zelda.jpg',
  metacritic: 99,
  genres: [{ name: 'Action' }, { name: 'Adventure' }],
  platforms: [{ platform: { name: 'Nintendo 64' } }, { platform: { name: 'Nintendo Switch' } }],
};

const mockRawgResponse = {
  results: [
    mockRawgGame,
    {
      name: 'No Image Game',
      released: '2000-01-01',
      genres: [],
      platforms: [],
    },
  ],
};

const mockIgdbGame = {
  name: 'The Legend of Zelda: Ocarina of Time',
  first_release_date: 909014400,
  genres: [{ name: 'Action' }, { name: 'Adventure' }],
  platforms: [{ name: 'Nintendo 64' }],
  total_rating: 97.4,
  cover: { image_id: 'zelda_cover' },
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../../../src/services/IgdbService.js', () => ({
  default: {
    getRandomGame: vi.fn(),
    coverUrl: vi.fn(
      (id: string) => `https://images.igdb.com/igdb/image/upload/t_cover_big_2x/${id}.jpg`,
    ),
    reset: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;
const mockGetRandomGame = IgdbService.getRandomGame as ReturnType<typeof vi.fn>;

describe('GameCommand', () => {
  let command: GameCommand;

  beforeEach(() => {
    command = new GameCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',game', true],
      [', game', true],
      [',game show', true],
      [',game dm', true],
      [',game show dm', true],
      ['  ,  game  ', true],
      ['game', false],
      [',game foo', false],
      ['hello', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    describe('IGDB source', () => {
      it('should return image from IGDB URL when IGDB succeeds', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { image: { url: string }; caption: string };
        expect(content.image.url).toContain('images.igdb.com');
        expect(content.caption).toContain('🎮 *The Legend of Zelda: Ocarina of Time* (1998)');
        expect(content.caption).toContain('🏷️ Action, Adventure');
        expect(content.caption).toContain('🖥️ Nintendo 64');
        expect(content.caption).toContain('⭐ 97/100');
      });

      it('should fall back to RAWG when IGDB throws', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB unavailable'));
        mockGet.mockResolvedValue({ data: mockRawgResponse });
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { image: { url: string } };
        expect(content.image.url).toContain('media.rawg.io');
      });
    });

    describe('RAWG source', () => {
      it('should return image and caption from RAWG when IGDB is unavailable', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB unavailable'));
        mockGet.mockResolvedValue({ data: mockRawgResponse });
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as {
          viewOnce: boolean;
          caption: string;
          image: { url: string };
        };
        expect(content.image.url).toBe(mockRawgGame.background_image);
        expect(content.caption).toContain('🎮 *The Legend of Zelda: Ocarina of Time* (1998)');
        expect(content.caption).toContain('🏷️ Action, Adventure');
        expect(content.caption).toContain('🖥️ Nintendo 64, Nintendo Switch');
        expect(content.caption).toContain('⭐ 99/100');
      });

      it('should call RAWG API with correct parameters when falling back', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB unavailable'));
        mockGet.mockResolvedValue({ data: mockRawgResponse });
        const data = GroupCommandData.build({ text: ',game' });

        await command.run(data);

        expect(AxiosClient.get).toHaveBeenCalledWith(
          'https://api.rawg.io/api/games',
          expect.objectContaining({
            params: expect.objectContaining({
              ordering: '-metacritic',
              page_size: 40,
            }),
          }),
        );
      });
    });

    describe('error cases', () => {
      it('should return error message when both IGDB and RAWG fail', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB failed'));
        mockGet.mockRejectedValue(new Error('RAWG failed'));
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Erro ao buscar jogo');
      });

      it('should return error message when RAWG returns no games with images', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB failed'));
        mockGet.mockResolvedValue({
          data: { results: [{ name: 'No Image', genres: [], platforms: [] }] },
        });
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages).toHaveLength(1);
        const content = messages[0].content as { text: string };
        expect(content.text).toContain('Erro ao buscar jogo');
      });
    });

    describe('flags', () => {
      it('should set viewOnce to true by default', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(true);
      });

      it('should set viewOnce to false with show flag', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game show' });

        const messages = await command.run(data);

        const content = messages[0].content as { viewOnce: boolean };
        expect(content.viewOnce).toBe(false);
      });

      it('should send to DM when dm flag is active in group', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.participant);
      });

      it('should not change jid when dm flag is active in private chat', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = PrivateCommandData.build({ text: ',game dm' });

        const messages = await command.run(data);

        expect(messages[0].jid).toBe(data.key.remoteJid);
      });
    });

    describe('RAWG caption edge cases', () => {
      it('should handle game with no metacritic score', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB unavailable'));
        mockGet.mockResolvedValue({
          data: {
            results: [
              {
                name: 'Indie Game',
                released: '2020-05-01',
                background_image: 'https://media.rawg.io/media/games/indie.jpg',
                genres: [{ name: 'Indie' }],
                platforms: [{ platform: { name: 'PC' } }],
              },
            ],
          },
        });
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).not.toContain('⭐');
        expect(content.caption).toContain('🎮 *Indie Game* (2020)');
      });

      it('should handle game with no platforms', async () => {
        mockGetRandomGame.mockRejectedValue(new Error('IGDB unavailable'));
        mockGet.mockResolvedValue({
          data: {
            results: [
              {
                name: 'Platform-less Game',
                released: '2010-01-01',
                background_image: 'https://media.rawg.io/media/games/plat.jpg',
                metacritic: 75,
                genres: [{ name: 'Strategy' }],
              },
            ],
          },
        });
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        const content = messages[0].content as { caption: string };
        expect(content.caption).toContain('🖥️ —');
      });
    });

    describe('message options', () => {
      it('should include ephemeral expiration from data', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game', expiration: 86400 });

        const messages = await command.run(data);

        expect(messages[0].options?.ephemeralExpiration).toBe(86400);
      });

      it('should quote the original message', async () => {
        mockGetRandomGame.mockResolvedValue(mockIgdbGame);
        const data = GroupCommandData.build({ text: ',game' });

        const messages = await command.run(data);

        expect(messages[0].options?.quoted).toBe(data);
      });
    });
  });
});
