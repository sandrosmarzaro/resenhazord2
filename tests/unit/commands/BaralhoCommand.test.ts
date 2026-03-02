import { describe, it, expect, beforeEach, vi } from 'vitest';
import BaralhoCommand from '../../../src/commands/BaralhoCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;

describe('BaralhoCommand', () => {
  let command: BaralhoCommand;

  beforeEach(() => {
    command = new BaralhoCommand();
    vi.clearAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', carta', true],
      [',carta', true],
      [', CARTA', true],
      [', carta show', true],
      [', carta dm', true],
      [', carta show dm', true],
      ['  , carta  ', true],
      ['carta', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return image with card from API', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string }; caption: string };
      expect(content.image.url).toBe('https://deckofcardsapi.com/static/img/KH.png');
      expect(content.caption).toContain('carta');
    });

    it('should call deckofcardsapi', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta' });

      await command.run(data);

      expect(mockGet).toHaveBeenCalledWith('https://deckofcardsapi.com/api/deck/new/draw/?count=1');
    });

    it('should set viewOnce to true by default', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = PrivateCommandData.build({ text: ',carta dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockGet.mockResolvedValue({
        data: { cards: [{ image: 'https://deckofcardsapi.com/static/img/KH.png' }] },
      });
      const data = GroupCommandData.build({ text: ',carta', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
