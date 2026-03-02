import { describe, it, expect, beforeEach, vi } from 'vitest';
import Rule34Command from '../../../src/commands/Rule34Command.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const buildHtml = (images: string[]) => {
  const imgTags = images.map((src) => `<img src="${src}">`).join('');
  return `<html><body><div class="flexi">${imgTags}</div></body></html>`;
};

describe('Rule34Command', () => {
  let command: Rule34Command;

  beforeEach(() => {
    command = new Rule34Command();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', rule 34', true],
      [',rule 34', true],
      [', RULE 34', true],
      [', rule 34 show', true],
      [', rule 34 dm', true],
      ['  , rule 34  ', true],
      ['rule 34', false],
      ['hello', false],
      [', rule 34 extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should parse HTML and return first image', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img1.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe('https://example.com/img1.jpg');
      expect(content.caption).toBeDefined();
    });

    it('should skip banner URL and use second image', async () => {
      const bannerUrl = 'https://kanako.store/products/futa-body';
      mockGet.mockResolvedValue({
        data: buildHtml([bannerUrl, 'https://example.com/real-img.jpg']),
      });
      const data = GroupCommandData.build({ text: ',rule 34' });

      const messages = await command.run(data);

      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe('https://example.com/real-img.jpg');
    });

    it('should throw error when no images found', async () => {
      mockGet.mockResolvedValue({ data: buildHtml([]) });
      const data = GroupCommandData.build({ text: ',rule 34' });

      await expect(command.run(data)).rejects.toThrow('Nenhuma imagem encontrada');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34 show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34 dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = PrivateCommandData.build({ text: ',rule 34 dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: buildHtml(['https://example.com/img.jpg']) });
      const data = GroupCommandData.build({ text: ',rule 34', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
