import { describe, it, expect, beforeEach, vi } from 'vitest';
import HeartstoneCommand from '../../../src/commands/HeartstoneCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = AxiosClient.get as ReturnType<typeof vi.fn>;
const mockPost = AxiosClient.post as ReturnType<typeof vi.fn>;

const mockCard = {
  name: 'Fireball',
  text: 'Deal <b>6</b> damage to a minion.',
  flavorText: 'This spell is useful for dealing with pesky minions.',
  image: 'https://d15f34w2p8l1cc.cloudfront.net/hearthstone/fireball.png',
};

describe('HeartstoneCommand', () => {
  let command: HeartstoneCommand;

  beforeEach(() => {
    command = new HeartstoneCommand();
    vi.clearAllMocks();
    process.env.BNET_ID = 'test-id';
    process.env.BNET_SECRET = 'test-secret';
  });

  describe('matches()', () => {
    it.each([
      [', hs', true],
      [',hs', true],
      [', HS', true],
      [', hs show', true],
      [', hs dm', true],
      ['  , hs  ', true],
      ['hs', false],
      ['hello', false],
      [', hs extra', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error when OAuth fails', async () => {
      mockPost.mockRejectedValue(new Error('OAuth Error'));
      const data = GroupCommandData.build({ text: ',hs' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Battle.net');
    });

    it('should return card with HTML tags replaced', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 10, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { caption: string; image: { url: string } };
      expect(content.image.url).toBe(mockCard.image);
      expect(content.caption).toContain('*Fireball*');
      expect(content.caption).toContain('*6*');
      expect(content.caption).not.toContain('<b>');
      expect(content.caption).not.toContain('</b>');
    });

    it('should set viewOnce to true by default', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = PrivateCommandData.build({ text: ',hs dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      mockPost.mockResolvedValue({ data: { access_token: 'mock-token' } });
      mockGet
        .mockResolvedValueOnce({ data: { pageCount: 1, cards: [] } })
        .mockResolvedValueOnce({ data: { cards: [mockCard] } });
      vi.spyOn(Math, 'random').mockReturnValue(0);
      const data = GroupCommandData.build({ text: ',hs', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
