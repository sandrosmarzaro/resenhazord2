import { describe, it, expect, beforeEach } from 'vitest';
import PromptCommand from '../../../src/commands/PromptCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';

describe('PromptCommand', () => {
  let command: PromptCommand;

  beforeEach(() => {
    command = new PromptCommand();
    process.env.GEMINI_API_KEY = 'test-api-key';
  });

  describe('matches()', () => {
    it.each([
      [', prompt', true],
      [',prompt', true],
      [', PROMPT', true],
      [', prompt hello world', true],
      ['  , prompt  ', true],
      ['prompt', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error when no text provided', async () => {
      const data = GroupCommandData.build({ text: ', prompt' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Burro burro');
      expect(content.text).toContain('texto para IA');
    });

    it('should return AI response text', async () => {
      const data = GroupCommandData.build({ text: ', prompt hello' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toBe('Mocked AI response');
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', prompt hello' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', prompt hello', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
