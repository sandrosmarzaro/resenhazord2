import { describe, it, expect, beforeEach, vi } from 'vitest';
import MusicCommand from '../../../src/commands/MusicCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';
import AxiosClient from '../../../src/infra/AxiosClient.js';

const mockTrack = {
  name: 'Test Song',
  artist_name: 'Test Artist',
  album_name: 'Test Album',
  duration: 185,
  releasedate: '2024-01-15',
  image: 'https://example.com/image.jpg',
  audio: 'https://example.com/audio.mp3',
};

vi.mock('../../../src/infra/AxiosClient.js', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('MusicCommand', () => {
  let command: MusicCommand;

  beforeEach(() => {
    command = new MusicCommand();
    vi.clearAllMocks();
    process.env.JAMENDO_CLIENT_ID = 'test_client_id';
  });

  describe('matches()', () => {
    it.each([
      [',musica', true],
      [', musica', true],
      [',música', true],
      [', música', true],
      [',musica rock', true],
      [', musica jazz', true],
      [',musica show', true],
      [',musica dm', true],
      [',musica rock show dm', true],
      [',musica rock show', true],
      [',musica rock dm', true],
      ['  ,  musica  ', true],
      ['musica', false],
      [',musica rock pop', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return 2 messages on success (image + audio)', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(2);
      const imageContent = messages[0].content as {
        viewOnce: boolean;
        caption: string;
        image: { url: string };
      };
      expect(imageContent.image.url).toBe(mockTrack.image);
      expect(imageContent.caption).toContain(mockTrack.name);
      expect(imageContent.caption).toContain(mockTrack.artist_name);
      expect(imageContent.caption).toContain(mockTrack.album_name);
      const audioContent = messages[1].content as {
        audio: { url: string };
        mimetype: string;
      };
      expect(audioContent.audio.url).toBe(mockTrack.audio);
      expect(audioContent.mimetype).toBe('audio/mp4');
    });

    it('should set viewOnce to true by default', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
      const audioContent = messages[1].content as { viewOnce: boolean };
      expect(audioContent.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica show' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
      const audioContent = messages[1].content as { viewOnce: boolean };
      expect(audioContent.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
      expect(messages[1].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = PrivateCommandData.build({ text: ',musica dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should return error message on API failure', async () => {
      vi.mocked(AxiosClient.get).mockRejectedValue(new Error('API Error'));
      const data = GroupCommandData.build({ text: ',musica' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Erro ao buscar música');
    });

    it('should return friendly message on empty results', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não encontrei músicas');
    });

    it('should use specified genre when valid', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica rock' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://api.jamendo.com/v3.0/tracks/',
        expect.objectContaining({
          params: expect.objectContaining({ tags: 'rock' }),
        }),
      );
    });

    it('should fall back to random genre for invalid genre', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica invalidgenre' });

      await command.run(data);

      expect(AxiosClient.get).toHaveBeenCalledWith(
        'https://api.jamendo.com/v3.0/tracks/',
        expect.objectContaining({
          params: expect.objectContaining({
            tags: expect.stringMatching(
              /^(rock|pop|electronic|hiphop|jazz|classical|metal|reggae|blues|country|folk|latin|rnb|punk|ambient|soul|funk|indie|techno|house)$/,
            ),
          }),
        }),
      );
    });

    it('should format duration correctly', () => {
      expect(command.formatDuration(185)).toBe('3:05');
      expect(command.formatDuration(60)).toBe('1:00');
      expect(command.formatDuration(0)).toBe('0:00');
      expect(command.formatDuration(59)).toBe('0:59');
    });

    it('should include ephemeral expiration from data', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
      expect(messages[1].options?.ephemeralExpiration).toBe(86400);
    });

    it('should quote the original message', async () => {
      vi.mocked(AxiosClient.get).mockResolvedValue({
        data: { results: [mockTrack] },
      } as never);
      const data = GroupCommandData.build({ text: ',musica' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
      expect(messages[1].options?.quoted).toBe(data);
    });
  });
});
