import { describe, it, expect, beforeEach, vi } from 'vitest';
import HentaiCommand from '../../../src/commands/HentaiCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

vi.mock('../../../src/scrapers/HentaiScraper.js', () => ({
  default: {
    getRandomGallery: vi.fn().mockResolvedValue({
      title: 'Test Manga',
      japaneseTitle: 'テストマンガ',
      artists: ['artist1'],
      groups: ['group1'],
      tags: ['tag1', 'tag2', 'tag3'],
      type: 'doujinshi',
      language: 'japanese',
      pages: 42,
      date: '2024-01',
      coverUrl: 'https://example.com/cover.webp',
      url: 'https://hitomi.la/galleries/123.html',
    }),
  },
}));

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    getBuffer: vi.fn().mockResolvedValue(Buffer.from('fake-image')),
  },
}));

import HentaiScraper from '../../../src/scrapers/HentaiScraper.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockGetRandomGallery = HentaiScraper.getRandomGallery as ReturnType<typeof vi.fn>;
const mockGetBuffer = AxiosClient.getBuffer as ReturnType<typeof vi.fn>;

describe('HentaiCommand', () => {
  let command: HentaiCommand;

  beforeEach(() => {
    command = new HentaiCommand();
    vi.clearAllMocks();
    mockGetRandomGallery.mockResolvedValue({
      title: 'Test Manga',
      japaneseTitle: 'テストマンガ',
      artists: ['artist1'],
      groups: ['group1'],
      tags: ['tag1', 'tag2', 'tag3'],
      type: 'doujinshi',
      language: 'japanese',
      pages: 42,
      date: '2024-01',
      coverUrl: 'https://example.com/cover.webp',
      url: 'https://hitomi.la/galleries/123.html',
    });
    mockGetBuffer.mockResolvedValue(Buffer.from('fake-image'));
  });

  describe('matches()', () => {
    it.each([
      [',hentai', true],
      [', hentai', true],
      [', HENTAI', true],
      [', hentai show', true],
      [', hentai dm', true],
      ['  , hentai  ', true],
      ['hentai', false],
      ['hello', false],
      [', hentai extra', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('returns one image message with caption containing the title', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].content).toHaveProperty('image');
      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('📖');
      expect(content.caption).toContain('Test Manga');
    });

    it('caption includes metadata fields', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('artist1');
      expect(content.caption).toContain('group1');
      expect(content.caption).toContain('doujinshi');
      expect(content.caption).toContain('japanese');
      expect(content.caption).toContain('42');
      expect(content.caption).toContain('2024-01');
      expect(content.caption).toContain('https://hitomi.la/galleries/123.html');
    });

    it('caption omits japanese title when same as title', async () => {
      mockGetRandomGallery.mockResolvedValueOnce({
        title: 'Same Title',
        japaneseTitle: 'Same Title',
        artists: [],
        groups: [],
        tags: [],
        type: 'manga',
        language: 'english',
        pages: 10,
        date: '2024-06',
        coverUrl: 'https://example.com/cover.webp',
        url: 'https://hitomi.la/galleries/1.html',
      });
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).not.toContain('🗾');
    });

    it('caption shows japanese title when different', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🗾');
      expect(content.caption).toContain('テストマンガ');
    });

    it('caption shows "—" when no artists', async () => {
      mockGetRandomGallery.mockResolvedValueOnce({
        title: 'No Artist',
        artists: [],
        groups: [],
        tags: [],
        type: 'manga',
        language: 'english',
        pages: 5,
        date: '2024-03',
        coverUrl: 'https://example.com/cover.webp',
        url: 'https://hitomi.la/galleries/2.html',
      });
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('✍️ —');
    });

    it('caption truncates tags beyond 10', async () => {
      mockGetRandomGallery.mockResolvedValueOnce({
        title: 'Many Tags',
        artists: [],
        groups: [],
        tags: Array.from({ length: 15 }, (_, i) => `tag${i + 1}`),
        type: 'manga',
        language: 'english',
        pages: 20,
        date: '2024-04',
        coverUrl: 'https://example.com/cover.webp',
        url: 'https://hitomi.la/galleries/3.html',
      });
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('+5 more');
    });

    it('sets viewOnce true by default', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('sets viewOnce false with show flag', async () => {
      const data = GroupCommandData.build({ text: ',hentai show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('sends to DM when dm flag is set in group', async () => {
      const data = GroupCommandData.build({ text: ',hentai dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('does not change jid when dm flag is set in private chat', async () => {
      const data = PrivateCommandData.build({ text: ',hentai dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('quotes the original message', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('includes ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ',hentai', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('fetches cover buffer using gallery coverUrl', async () => {
      const data = GroupCommandData.build({ text: ',hentai' });

      await command.run(data);

      expect(mockGetBuffer).toHaveBeenCalledWith('https://example.com/cover.webp', { retries: 0 });
    });

    it('retries up to 3 times when cover fetch fails, succeeding on 3rd attempt', async () => {
      const error = new Error('404');
      mockGetBuffer.mockRejectedValueOnce(error).mockRejectedValueOnce(error);
      const data = GroupCommandData.build({ text: ',hentai' });

      const messages = await command.run(data);

      expect(mockGetBuffer).toHaveBeenCalledTimes(3);
      expect(messages).toHaveLength(1);
    });

    it('throws after 3 failed cover fetches', async () => {
      const error = new Error('404');
      mockGetBuffer.mockRejectedValue(error);
      const data = GroupCommandData.build({ text: ',hentai' });

      await expect(command.run(data)).rejects.toThrow('404');
      expect(mockGetBuffer).toHaveBeenCalledTimes(3);
    });
  });
});
