import { describe, it, expect, beforeEach } from 'vitest';
import ImageCommand from '../../../src/commands/ImageCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

describe('ImageCommand', () => {
  let command: ImageCommand;

  beforeEach(() => {
    command = new ImageCommand();
  });

  describe('matches()', () => {
    it.each([
      [', img a cat', true],
      [',img a cat', true],
      [', IMG a cat', true],
      [', img hd a cat', true],
      [', img 4k a cat', true],
      [', img flux-pro a cat', true],
      [', img show a cat', true],
      [', img dm a cat', true],
      [', img hd flux-anime show dm a cat', true],
      ['  , img  a cat', true],
      ['img', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error when no prompt is provided', async () => {
      const data = GroupCommandData.build({ text: ', img' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('texto para a imagem');
    });

    it('should return image with correct URL structure', async () => {
      const data = GroupCommandData.build({ text: ', img a beautiful sunset' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toContain('pollinations.ai');
      expect(content.image.url).toContain('a%20beautiful%20sunset');
    });

    it('should use custom resolution when specified', async () => {
      const data = GroupCommandData.build({ text: ', img hd a cat' });

      const messages = await command.run(data);

      const content = messages[0].content as { image: { url: string } };
      expect(content.image.url).toContain('width=720');
      expect(content.image.url).toContain('height=1280');
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ', img a cat' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ', img show a cat' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ', img dm a cat' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', img dm a cat' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', img a cat' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', img a cat', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
