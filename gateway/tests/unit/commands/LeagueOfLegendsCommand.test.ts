import { describe, it, expect, beforeEach, vi } from 'vitest';
import LeagueOfLegendsCommand from '../../../src/commands/LeagueOfLegendsCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockChampion = {
  id: 'Ahri',
  name: 'Ahri',
  title: 'a Raposa de Nove Caudas',
  tags: ['Mage', 'Assassin'],
  info: { attack: 3, defense: 4, magic: 8, difficulty: 5 },
  blurb: 'Ahri é uma vastaya conectada de maneira inata ao mundo espiritual.',
};

const mockVersionResponse = { data: ['14.10.1', '14.9.1'] };

const mockChampionListResponse = {
  data: {
    data: {
      Ahri: mockChampion,
      Garen: {
        id: 'Garen',
        name: 'Garen',
        title: 'o Poder de Demacia',
        tags: ['Fighter', 'Tank'],
        info: { attack: 7, defense: 7, magic: 1, difficulty: 5 },
        blurb: 'Um guerreiro nobre e orgulhoso.',
      },
    },
  },
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('LeagueOfLegendsCommand', () => {
  let command: LeagueOfLegendsCommand;

  beforeEach(() => {
    command = new LeagueOfLegendsCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [',lol', true],
      [', lol', true],
      [',lol show', true],
      [',lol dm', true],
      [',lol show dm', true],
      ['  ,  lol  ', true],
      ['lol', false],
      [',lol foo', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return 1 message with image and caption on success', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as {
        viewOnce: boolean;
        caption: string;
        image: { url: string };
      };
      expect(content.image.url).toMatch(
        /^https:\/\/ddragon\.leagueoflegends\.com\/cdn\/img\/champion\/splash\/.+_0\.jpg$/,
      );
      expect(content.caption).toContain('Ataque:');
      expect(content.caption).toContain('Defesa:');
      expect(content.caption).toContain('Magia:');
      expect(content.caption).toContain('Dificuldade:');
    });

    it('should call Data Dragon API with correct URLs', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://ddragon.leagueoflegends.com/api/versions.json',
        expect.objectContaining({ timeout: 15000 }),
      );
      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://ddragon.leagueoflegends.com/cdn/14.10.1/data/pt_BR/champion.json',
        expect.objectContaining({ timeout: 15000 }),
      );
    });

    it('should set viewOnce to true by default', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = PrivateCommandData.build({ text: ',lol dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should return error message when API fails', async () => {
      mockGet.mockRejectedValue(new Error('API Error'));
      const data = GroupCommandData.build({ text: ',lol' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar campeão de LoL');
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should quote the original message', async () => {
      mockGet
        .mockResolvedValueOnce(mockVersionResponse)
        .mockResolvedValueOnce(mockChampionListResponse);
      const data = GroupCommandData.build({ text: ',lol' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should display role emojis in caption', async () => {
      mockGet.mockResolvedValueOnce(mockVersionResponse).mockResolvedValueOnce({
        data: {
          data: {
            Ahri: mockChampion,
          },
        },
      });
      const data = GroupCommandData.build({ text: ',lol' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('🔮 Mage');
      expect(content.caption).toContain('🗡️ Assassin');
    });
  });
});
