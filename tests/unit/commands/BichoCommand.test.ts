import { describe, it, expect, beforeEach, vi } from 'vitest';
import BichoCommand from '../../../src/commands/BichoCommand.js';
import BichoScraper from '../../../src/scrapers/BichoScraper.js';
import type { DrawResult } from '../../../src/scrapers/BichoScraper.js';
import { GroupCommandData } from '../../fixtures/index.js';

vi.mock('../../../src/scrapers/BichoScraper.js', () => ({
  default: { fetch: vi.fn() },
}));

const mockFetch = BichoScraper.fetch as ReturnType<typeof vi.fn>;

const makeDraw = (overrides: Partial<DrawResult> = {}): DrawResult => ({
  id: 'PTN',
  label: 'PTN 18h',
  published: true,
  prizes: [
    { prize: 1, milhar: '4321', animal: 'Gato', group: 14, emoji: '🐱' },
    { prize: 2, milhar: '8765', animal: 'Leão', group: 16, emoji: '🦁' },
    { prize: 3, milhar: '1234', animal: 'Águia', group: 2, emoji: '🦅' },
    { prize: 4, milhar: '5678', animal: 'Porco', group: 18, emoji: '🐷' },
    { prize: 5, milhar: '9012', animal: 'Jacaré', group: 15, emoji: '🐊' },
  ],
  ...overrides,
});

const allDraws = (published: string[] = []): DrawResult[] => [
  { id: 'PPT', label: 'PPT 9h', published: published.includes('PPT'), prizes: [] },
  { id: 'PTM', label: 'PTM 11h', published: published.includes('PTM'), prizes: [] },
  { id: 'PT', label: 'PT 14h', published: published.includes('PT'), prizes: [] },
  { id: 'PTV', label: 'PTV 16h', published: published.includes('PTV'), prizes: [] },
  { id: 'PTN', label: 'PTN 18h', published: published.includes('PTN'), prizes: [] },
  { id: 'COR', label: 'Coruja 21h', published: published.includes('COR'), prizes: [] },
];

describe('BichoCommand', () => {
  let command: BichoCommand;

  beforeEach(() => {
    command = new BichoCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',bicho', true],
      [', bicho', true],
      [', BICHO', true],
      [',bicho ppt', true],
      [',bicho ptm', true],
      [',bicho pt', true],
      [',bicho ptv', true],
      [',bicho ptn', true],
      [',bicho cor', true],
      [',bicho PPT', true],
      ['  , bicho  ', true],
      ['bicho', false],
      ['hello', false],
      [',bicho extra', false],
      [',bicho ppt extra', false],
    ])('"%s" → %s', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('returns the most recent published draw when no arg given', async () => {
      const ptnDraw = makeDraw();
      const draws = [
        ...allDraws(['PPT', 'PTM', 'PT', 'PTV']).slice(0, 4),
        ptnDraw,
        { id: 'COR', label: 'Coruja 21h', published: false, prizes: [] },
      ];
      mockFetch.mockResolvedValue(draws);
      const data = GroupCommandData.build({ text: ',bicho' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('PTN 18h');
      expect(content.text).toContain('4321');
      expect(content.text).toContain('Gato');
    });

    it('returns a specific draw when arg is given', async () => {
      const pptDraw = makeDraw({
        id: 'PPT',
        label: 'PPT 9h',
        prizes: [{ prize: 1, milhar: '0092', animal: 'Urso', group: 23, emoji: '🐻' }],
      });
      mockFetch.mockResolvedValue([pptDraw, ...allDraws().slice(1)]);
      const data = GroupCommandData.build({ text: ',bicho ppt' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('PPT 9h');
      expect(content.text).toContain('0092');
      expect(content.text).toContain('Urso');
    });

    it('returns pending message when requested draw is not published', async () => {
      mockFetch.mockResolvedValue(allDraws());
      const data = GroupCommandData.build({ text: ',bicho cor' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Coruja 21h');
      expect(content.text).toContain('não foi publicado');
    });

    it('returns no-draw message when no draws published and no arg given', async () => {
      mockFetch.mockResolvedValue(allDraws());
      const data = GroupCommandData.build({ text: ',bicho' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Nenhum sorteio publicado');
    });

    it('formats prizes with emoji and milhar', async () => {
      mockFetch.mockResolvedValue([makeDraw()]);
      const data = GroupCommandData.build({ text: ',bicho ptn' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('1️⃣');
      expect(content.text).toContain('🐱 *Gato* (grupo 14)');
      expect(content.text).toContain('2️⃣');
      expect(content.text).toContain('🦁 *Leão* (grupo 16)');
    });

    it('returns error message on fetch failure', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));
      const data = GroupCommandData.build({ text: ',bicho' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar resultados do Jogo do Bicho');
    });

    it('quotes the original message', async () => {
      mockFetch.mockResolvedValue([makeDraw()]);
      const data = GroupCommandData.build({ text: ',bicho ptn' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });
  });
});
