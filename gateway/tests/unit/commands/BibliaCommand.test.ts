import { describe, it, expect, beforeEach, vi } from 'vitest';
import BibliaCommand from '../../../src/commands/BibliaCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockVerse = {
  book: { name: 'Gênesis' },
  chapter: 1,
  number: 1,
  text: 'No princípio, Deus criou os céus e a terra.',
};

const mockBooks = [
  { name: 'Gênesis', abbrev: { pt: 'gn' } },
  { name: 'Êxodo', abbrev: { pt: 'ex' } },
  { name: 'Salmos', abbrev: { pt: 'sl' } },
];

describe('BibliaCommand', () => {
  let command: BibliaCommand;

  beforeEach(() => {
    command = new BibliaCommand();
    vi.clearAllMocks();
    process.env.BIBLIA_TOKEN = 'test-token';
  });

  describe('matches()', () => {
    it.each([
      [', bíblia', true],
      [',bíblia', true],
      [', biblia', true],
      [', BÍBLIA', true],
      [', bíblia nvi', true],
      [', bíblia ra', true],
      [', bíblia Gênesis 1:1', true],
      [', bíblia Gênesis 1:1-3', true],
      [', bíblia pt nvi Gênesis 1:1', true],
      ['  , bíblia  ', true],
      ['bíblia', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return random verse when no book/chapter specified', async () => {
      mockGet.mockResolvedValue({ data: mockVerse });
      const data = GroupCommandData.build({ text: ', bíblia' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('*Gênesis 1:1*');
      expect(content.text).toContain('No princípio');
    });

    it('should return specific verse with book+chapter:number', async () => {
      mockGet.mockResolvedValueOnce({ data: mockBooks }).mockResolvedValueOnce({ data: mockVerse });
      const data = GroupCommandData.build({ text: ', bíblia Gênesis 1:1' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('*Gênesis 1:1*');
    });

    it('should return verse range', async () => {
      mockGet
        .mockResolvedValueOnce({ data: mockBooks })
        .mockResolvedValueOnce({ data: { ...mockVerse, number: 1 } })
        .mockResolvedValueOnce({
          data: { ...mockVerse, number: 2, text: 'A terra era sem forma e vazia.' },
        });
      const data = GroupCommandData.build({ text: ', bíblia Gênesis 1:1-2' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('*Gênesis 1:1-2*');
      expect(content.text).toContain('No princípio');
      expect(content.text).toContain('A terra era sem forma e vazia.');
    });

    it('should return error when book is not found', async () => {
      mockGet.mockResolvedValueOnce({ data: mockBooks });
      const data = GroupCommandData.build({ text: ', bíblia Inexistente 1:1' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não consegui encontrar o livro');
      expect(content.text).toContain('Livros Disponíveis');
    });

    it('should return error when no book name is provided', async () => {
      const data = GroupCommandData.build({ text: ', bíblia 1:1' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('nome do livro');
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockVerse });
      const data = GroupCommandData.build({ text: ', bíblia' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: mockVerse });
      const data = GroupCommandData.build({ text: ', bíblia', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
