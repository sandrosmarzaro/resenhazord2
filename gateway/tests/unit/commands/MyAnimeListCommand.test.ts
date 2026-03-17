import { describe, it, expect, beforeEach, vi } from 'vitest';
import MyAnimeListCommand from '../../../src/commands/MyAnimeListCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockAnime = {
  title: 'Naruto',
  images: { webp: { large_image_url: 'https://cdn.myanimelist.net/naruto.webp' } },
  genres: [{ name: 'Action' }],
  themes: [{ name: 'Martial Arts' }],
  demographics: [{ name: 'Shounen' }],
  studios: [{ name: 'Pierrot' }],
  aired: { prop: { from: { year: 2002 } } },
  episodes: 220,
  score: 8.0,
  rank: 500,
};

const mockManga = {
  title: 'One Piece',
  images: { webp: { large_image_url: 'https://cdn.myanimelist.net/onepiece.webp' } },
  genres: [{ name: 'Adventure' }],
  themes: [{ name: 'Pirates' }],
  demographics: [{ name: 'Shounen' }],
  authors: [{ name: 'Oda, Eiichiro' }],
  published: { prop: { from: { year: 1997 } } },
  chapters: 1100,
  score: 9.2,
  rank: 5,
};

describe('MyAnimeListCommand', () => {
  let command: MyAnimeListCommand;

  beforeEach(() => {
    command = new MyAnimeListCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', anime', true],
      [',anime', true],
      [', ANIME', true],
      [', manga', true],
      [',manga', true],
      [', anime show', true],
      [', anime dm', true],
      ['  , anime  ', true],
      ['anime', false],
      ['manga', false],
      ['hello', false],
      [', anime extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return anime with studios and episodes', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { caption: string; image: { url: string } };
      expect(content.image.url).toBe('https://cdn.myanimelist.net/naruto.webp');
      expect(content.caption).toContain('*Naruto*');
      expect(content.caption).toContain('🎙️');
      expect(content.caption).toContain('Pierrot');
      expect(content.caption).toContain('🎥 220x');
      expect(content.caption).toContain('2002');
    });

    it('should return manga with authors and chapters', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockManga] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',manga' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*One Piece*');
      expect(content.caption).toContain('🖋');
      expect(content.caption).toContain('Oda, Eiichiro');
      expect(content.caption).toContain('📚 1100x');
      expect(content.caption).toContain('1997');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',anime dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: { data: [mockAnime] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',anime', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
