import { describe, it, expect, beforeEach, vi } from 'vitest';
import CountryFlagCommand from '../../../src/commands/CountryFlagCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockBrazil = {
  name: { common: 'Brasil', official: 'República Federativa do Brasil' },
  flags: { png: 'https://flagcdn.com/w320/br.png' },
  flag: '🇧🇷',
  capital: ['Brasília'],
  region: 'Americas',
  subregion: 'South America',
  population: 215313498,
  area: 8515767,
  languages: { por: 'Portuguese' },
  currencies: { BRL: { name: 'Real', symbol: 'R$' } },
  timezones: ['UTC-05:00', 'UTC-04:00', 'UTC-03:00', 'UTC-02:00'],
  landlocked: false,
  unMember: true,
  car: { side: 'right' },
};

const mockAntarctica = {
  name: { common: 'Antarctica', official: 'Antarctica' },
  flags: { png: 'https://flagcdn.com/w320/aq.png' },
  flag: '🇦🇶',
  capital: undefined,
  region: 'Antarctic',
  subregion: undefined,
  population: 1000,
  area: 14000000,
  languages: undefined,
  currencies: undefined,
  timezones: ['UTC+00:00'],
  landlocked: false,
  unMember: false,
  car: { side: 'right' },
};

describe('CountryFlagCommand', () => {
  let command: CountryFlagCommand;

  beforeEach(() => {
    command = new CountryFlagCommand();
    vi.clearAllMocks();
    vi.spyOn(Math, 'random').mockReturnValue(0);
  });

  describe('matches()', () => {
    it.each([
      [',bandeira', true],
      [', bandeira', true],
      [', BANDEIRA', true],
      [', bandeira show', true],
      [', bandeira dm', true],
      ['bandeira', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return 1 message with image url from flags.png', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toBe(mockBrazil.flags.png);
    });

    it('should include common name and flag emoji in caption', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*Brasil*');
      expect(content.caption).toContain('🇧🇷');
    });

    it('should include official name subtitle when different from common', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('_República Federativa do Brasil_');
    });

    it('should not include subtitle when official equals common', async () => {
      mockGet.mockResolvedValue({ data: [mockAntarctica] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      const lines = content.caption.split('\n');
      const subtitleLine = lines.find((l) => l.startsWith('_') && l.endsWith('_'));
      expect(subtitleLine).toBeUndefined();
    });

    it('should include capital in caption', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🏙️ Capital: Brasília');
    });

    it('should include region emoji and PT-BR label', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🌎');
      expect(content.caption).toContain('Américas');
    });

    it('should include translated subregion', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('América do Sul');
    });

    it('should include formatted population', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('habitantes');
      expect(content.caption).toMatch(/\d[\d.,\s]*habitantes/);
    });

    it('should include formatted area with km²', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('km²');
    });

    it('should include language name', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Portuguese');
    });

    it('should include currency name with ISO code in parentheses', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Real (BRL)');
    });

    it('should include UN membership and landlocked status', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('ONU: ✅');
      expect(content.caption).toContain('Sem litoral: ❌');
    });

    it('should show single timezone without separator', async () => {
      mockGet.mockResolvedValue({ data: [mockAntarctica] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('UTC+00:00');
      expect(content.caption).not.toContain(' a ');
    });

    it('should join multiple timezones with " a "', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('UTC-05:00 a UTC-02:00');
    });

    it('should show Direita for right-hand traffic', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Direita');
    });

    it('should show Esquerda for left-hand traffic', async () => {
      const mockLeftDrive = { ...mockBrazil, car: { side: 'left' as const } };
      mockGet.mockResolvedValue({ data: [mockLeftDrive] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('Esquerda');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = PrivateCommandData.build({ text: ',bandeira dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({ data: [mockBrazil] });
      const data = GroupCommandData.build({ text: ',bandeira', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should return error text on API failure', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar bandeira');
    });

    it('should show N/A for missing capital', async () => {
      mockGet.mockResolvedValue({ data: [mockAntarctica] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🏙️ Capital: N/A');
    });

    it('should show N/A for missing languages', async () => {
      mockGet.mockResolvedValue({ data: [mockAntarctica] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🗣️ N/A');
    });

    it('should show N/A for missing currencies', async () => {
      mockGet.mockResolvedValue({ data: [mockAntarctica] });
      const data = GroupCommandData.build({ text: ',bandeira' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('💰 N/A');
    });
  });
});
