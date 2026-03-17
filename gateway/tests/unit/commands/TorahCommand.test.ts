import { describe, it, expect, beforeEach, vi } from 'vitest';
import TorahCommand from '../../../src/commands/TorahCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockVerseResponse = {
  data: {
    ref: 'Genesis 1:1',
    text: 'When God began to create heaven and earth— ',
    he: '<big>בְּ</big>רֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ׃',
    heTitle: 'בראשית',
  },
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('TorahCommand', () => {
  let command: TorahCommand;

  beforeEach(() => {
    command = new TorahCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',tora', true],
      [',torá', true],
      [', tora', true],
      ['  ,  tora  ', true],
      [',tora en', true],
      [',tora he', true],
      [',tora Genesis 1:1', true],
      ['tora', false],
      ['hello', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('returns bilingual formatted verse for random (no args)', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('*Genesis 1:1 — בראשית*');
      expect(content.text).toContain('> בְּרֵאשִׁ֖ית');
      expect(content.text).toContain('> When God began to create');
    });

    it('calls Sefaria API with a valid ref for random verse', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        expect.stringMatching(
          /^https:\/\/www\.sefaria\.org\/api\/texts\/\w+\.\d+\.\d+\?context=0$/,
        ),
      );
    });

    it('calls Sefaria API with the specific ref when args provided', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora Genesis 1:1' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://www.sefaria.org/api/texts/Genesis.1.1?context=0',
      );
    });

    it('returns English-only when lang en', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora en' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('> When God began to create');
      expect(content.text).not.toContain('> בְּרֵאשִׁ֖ית');
    });

    it('returns Hebrew-only when lang he', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora he' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('> בְּרֵאשִׁ֖ית');
      expect(content.text).not.toContain('> When God began to create');
    });

    it('strips HTML tags from text and he fields', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora he' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).not.toContain('<big>');
      expect(content.text).not.toContain('</big>');
    });

    it('returns error message with book list when API returns error', async () => {
      mockGet.mockResolvedValue({ data: { error: 'Not found' } });
      const data = GroupCommandData.build({ text: ',tora InvalidBook 1:1' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Versículo não encontrado');
      expect(content.text).toContain('Genesis (בראשית)');
      expect(content.text).toContain('Deuteronomy (דברים)');
    });

    it('returns error message when args do not match book chapter:verse pattern', async () => {
      const data = GroupCommandData.build({ text: ',tora invalid' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Versículo não encontrado');
    });

    it('quotes the original message', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('includes ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue(mockVerseResponse);
      const data = GroupCommandData.build({ text: ',tora', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
