import { describe, it, expect, beforeEach } from 'vitest';
import MediaCommand from '../../../src/commands/MediaCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';

describe('MediaCommand', () => {
  let command: MediaCommand;

  beforeEach(() => {
    command = new MediaCommand();
  });

  describe('matches()', () => {
    it.each([
      [', media', true],
      [',media', true],
      [', MEDIA', true],
      [', media https://example.com', true],
      ['  , media  ', true],
      ['media', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should prompt for URL when no URL is provided', async () => {
      const data = GroupCommandData.build({ text: ', media' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('link do vídeo');
    });

    it('should return always-fail message when URL is provided', async () => {
      const data = GroupCommandData.build({ text: ', media https://example.com/video' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não consegui baixar');
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', media' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', media', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
