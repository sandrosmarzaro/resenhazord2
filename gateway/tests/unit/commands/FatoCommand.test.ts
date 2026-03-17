import { describe, it, expect, beforeEach, vi } from 'vitest';
import FatoCommand from '../../../src/commands/FatoCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('FatoCommand', () => {
  let command: FatoCommand;

  beforeEach(() => {
    command = new FatoCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', fato', true],
      [',fato', true],
      [', FATO', true],
      [', fato hoje', true],
      [',fato hoje', true],
      ['  , fato  ', true],
      ['fato', false],
      ['hello', false],
      [', fato extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should call random endpoint by default', async () => {
      mockGet.mockResolvedValue({ data: { text: 'A random fact' } });
      const data = GroupCommandData.build({ text: ', fato' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith('https://uselessfacts.jsph.pl/api/v2/facts/random');
    });

    it('should call today endpoint when "hoje" is specified', async () => {
      mockGet.mockResolvedValue({ data: { text: 'Today fact' } });
      const data = GroupCommandData.build({ text: ', fato hoje' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith('https://uselessfacts.jsph.pl/api/v2/facts/today');
    });

    it('should return formatted text with FATO prefix', async () => {
      mockGet.mockResolvedValue({ data: { text: 'Cats sleep 70% of their lives.' } });
      const data = GroupCommandData.build({ text: ', fato' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('FATO');
      expect(content.text).toContain('Cats sleep 70% of their lives.');
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: { text: 'A fact' } });
      const data = GroupCommandData.build({ text: ', fato' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: { text: 'A fact' } });
      const data = GroupCommandData.build({ text: ', fato', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
