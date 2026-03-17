import { describe, it, expect, beforeEach, vi } from 'vitest';
import FilmeSerieCommand from '../../../src/commands/FilmeSerieCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockMovie = {
  poster_path: '/abc123.jpg',
  genre_ids: [28, 12],
  release_date: '2024-06-15',
  title: 'Test Movie',
  vote_average: 8.5,
  overview: 'An amazing test movie.',
};

const mockSerie = {
  poster_path: '/def456.jpg',
  genre_ids: [18],
  first_air_date: '2023-01-10',
  name: 'Test Serie',
  vote_average: 9.0,
  overview: 'An amazing test serie.',
};

const mockGenres = {
  genres: [
    { id: 28, name: 'Ação' },
    { id: 12, name: 'Aventura' },
    { id: 18, name: 'Drama' },
  ],
};

describe('FilmeSerieCommand', () => {
  let command: FilmeSerieCommand;

  beforeEach(() => {
    command = new FilmeSerieCommand();
    vi.clearAllMocks();
    process.env.TMDB_API_KEY = 'test-api-key';
  });

  describe('matches()', () => {
    it.each([
      [', filme', true],
      [',filme', true],
      [', FILME', true],
      [', série', true],
      [', serie', true],
      [', filme top', true],
      [', filme pop', true],
      [', filme show', true],
      [', filme dm', true],
      ['  , filme  ', true],
      ['filme', false],
      ['hello', false],
      [', filme extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return movie with caption', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toContain('image.tmdb.org');
      expect(content.caption).toContain('*Test Movie*');
      expect(content.caption).toContain('Ação, Aventura');
      expect(content.caption).toContain('8.5');
      expect(content.caption).toContain('2024');
    });

    it('should use tv type for série', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockSerie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',série' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*Test Serie*');
      expect(content.caption).toContain('2023');
    });

    it('should use top_rated mode when top is specified', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme top' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('top_rated'), expect.anything());
    });

    it('should use popular mode by default', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('popular'), expect.anything());
    });

    it('should set viewOnce to true by default', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',filme dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet
        .mockResolvedValueOnce({ data: { results: [mockMovie] } })
        .mockResolvedValueOnce({ data: mockGenres });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',filme', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
