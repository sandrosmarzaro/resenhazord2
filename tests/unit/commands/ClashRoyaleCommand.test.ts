import { describe, it, expect, beforeEach, vi } from 'vitest';
import ClashRoyaleCommand from '../../../src/commands/ClashRoyaleCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

const mockCards = [
  {
    key: 'knight',
    name: 'Knight',
    elixir: 3,
    type: 'Troop',
    rarity: 'Common',
    arena: 0,
    description: "A tough melee fighter. The Barbarian's handsome, cultured cousin.",
  },
];

describe('ClashRoyaleCommand', () => {
  let command: ClashRoyaleCommand;

  beforeEach(() => {
    command = new ClashRoyaleCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', cr', true],
      [',cr', true],
      [', CR', true],
      [', cr show', true],
      [', cr dm', true],
      ['  , cr  ', true],
      ['cr', false],
      ['hello', false],
      [', cr extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return image with correct card URL', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toContain('cards/knight.png');
    });

    it('should include card metadata in caption', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr' });

      const messages = await command.run(data);

      const content = messages[0].content as { caption: string };
      expect(content.caption).toContain('*Knight*');
      expect(content.caption).toContain('⚡ 3');
      expect(content.caption).toContain('🗡️ Troop');
      expect(content.caption).toContain('⚪ Common');
      expect(content.caption).toContain('Arena 0');
      expect(content.caption).toContain('A tough melee fighter');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = PrivateCommandData.build({ text: ',cr dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({ data: mockCards });
      const data = GroupCommandData.build({ text: ',cr' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should return error message on failure', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));
      const data = GroupCommandData.build({ text: ',cr' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar carta de Clash Royale');
    });
  });
});
