import { describe, it, expect, beforeEach, vi } from 'vitest';
import AlcoranCommand from '../../../src/commands/AlcoranCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockAyahResponse = {
  data: {
    text: 'E quando um deles recebe a notícia do nascimento de uma filha, seu rosto se ensombrece e fica angustiado.',
    numberInSurah: 17,
    surah: {
      number: 43,
      name: 'سُورَةُ الزُّخۡرُفِ',
      englishName: 'Az-Zukhruf',
      numberOfAyahs: 89,
    },
  },
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('AlcoranCommand', () => {
  let command: AlcoranCommand;

  beforeEach(() => {
    command = new AlcoranCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',alcorão', true],
      [', alcorão', true],
      [',alcorao', true],
      [', alcorao', true],
      ['  ,  alcorão  ', true],
      ['  ,  alcorao  ', true],
      ['alcorão', false],
      ['alcorao', false],
      [',alcorão extra', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return formatted verse message', async () => {
      mockGet.mockResolvedValue({ data: mockAyahResponse });
      const data = GroupCommandData.build({ text: ',alcorão' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('*Az-Zukhruf 43:17*');
      expect(content.text).toContain('> E quando um deles');
    });

    it('should call the Al Quran API with a random ayah number', async () => {
      mockGet.mockResolvedValue({ data: mockAyahResponse });
      const data = GroupCommandData.build({ text: ',alcorão' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        expect.stringMatching(/^https:\/\/api\.alquran\.cloud\/v1\/ayah\/\d+\/pt\.elhayek$/),
      );
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockAyahResponse });
      const data = GroupCommandData.build({ text: ',alcorão' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: mockAyahResponse });
      const data = GroupCommandData.build({ text: ',alcorão', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
