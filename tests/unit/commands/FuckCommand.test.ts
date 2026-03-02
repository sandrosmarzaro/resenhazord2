import { describe, it, expect, beforeEach, vi } from 'vitest';
import FuckCommand from '../../../src/commands/FuckCommand.js';
import { PrivateCommandData, MentionCommandData } from '../../fixtures/index.js';

describe('FuckCommand', () => {
  let command: FuckCommand;

  beforeEach(() => {
    command = new FuckCommand();
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', fuck @123456789 ', true],
      [',fuck @123456789 ', true],
      [', FUCK @123456789 ', true],
      ['fuck', false],
      ['hello', false],
      [', fuck', false],
      [', fuck @123 @456 ', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', fuck @123456789 ' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Burro burro');
      expect(content.text).toContain('grupo');
    });

    it('should return video with caption mentioning both users', async () => {
      const targetJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([targetJid]).build({
        text: ', fuck @5511999999999 ',
      });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as {
        video: { url: string };
        caption: string;
        mentions: string[];
        viewOnce: boolean;
      };
      expect(content.video.url).toBeDefined();
      expect(content.caption).toContain('fudendo');
      expect(content.mentions).toHaveLength(2);
      expect(content.viewOnce).toBe(true);
    });

    it('should quote the original message', async () => {
      const targetJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([targetJid]).build({
        text: ', fuck @5511999999999 ',
      });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const targetJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([targetJid]).build({
        text: ', fuck @5511999999999 ',
        expiration: 86400,
      });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
