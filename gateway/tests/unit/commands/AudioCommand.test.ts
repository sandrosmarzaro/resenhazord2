import { describe, it, expect, beforeEach } from 'vitest';
import AudioCommand from '../../../src/commands/AudioCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

describe('AudioCommand', () => {
  let command: AudioCommand;

  beforeEach(() => {
    command = new AudioCommand();
  });

  describe('matches()', () => {
    it.each([
      [', áudio hello', true],
      [',áudio hello', true],
      [', audio hello', true],
      [', ÁUDIO hello', true],
      [', áudio pt-br hello', true],
      [', áudio en-us hello', true],
      [', áudio show hello', true],
      [', áudio dm hello', true],
      ['  , áudio  hello', true],
      ['áudio', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error for invalid language', async () => {
      const data = GroupCommandData.build({ text: ', áudio xx-yy hello' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('idioma');
    });

    it('should return error when no text provided', async () => {
      const data = GroupCommandData.build({ text: ', áudio' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Cadê o texto');
    });

    it('should return single audio message for short text', async () => {
      const data = GroupCommandData.build({ text: ', áudio Hello world' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { audio: { url: string }; mimetype: string };
      expect(content.mimetype).toBe('audio/mp4');
      expect(content.audio.url).toBeDefined();
    });

    it('should set viewOnce to true by default', async () => {
      const data = GroupCommandData.build({ text: ', áudio Hello world' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(true);
    });

    it('should set viewOnce to false with show flag', async () => {
      const data = GroupCommandData.build({ text: ', áudio show Hello world' });

      const messages = await command.run(data);

      const content = messages[0].content as { viewOnce: boolean };
      expect(content.viewOnce).toBe(false);
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ', áudio dm Hello world' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', áudio dm Hello world' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', áudio Hello world' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', áudio Hello world', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
