import { describe, it, expect, beforeEach } from 'vitest';
import MateusCommand from '../../../src/commands/MateusCommand.js';
import { GroupCommandData } from '../../fixtures/index.js';

describe('MateusCommand', () => {
  let command: MateusCommand;

  beforeEach(() => {
    command = new MateusCommand();
  });

  describe('matches()', () => {
    it.each([
      [', mateus', true],
      [',mateus', true],
      [', MATEUS', true],
      [',MATEUS', true],
      ['  , mateus  ', true],
      ['\t,\tmateus\t', true],
      ['mateus', false],
      ['hello', false],
      [', mateus test', false],
      [', mateusinho', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return probability in X,XX % format', async () => {
      const data = GroupCommandData.build({ text: ', mateus' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/\d{1,3},\d{2} %/);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', mateus' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', mateus', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
