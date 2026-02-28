import { describe, it, expect, beforeEach } from 'vitest';
import D20Command from '../../../src/commands/D20Command.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

describe('D20Command', () => {
  let command: D20Command;

  beforeEach(() => {
    command = new D20Command();
  });

  describe('matches()', () => {
    it.each([
      [', d20', true],
      [',d20', true],
      [', D20', true],
      [',D20', true],
      ['  , d20  ', true],
      ['\t,\td20\t', true],
      ['d20', false],
      [', d20 extra', false],
      [', d200', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return message with dice roll result', async () => {
      const data = GroupCommandData.build({ text: ', d20' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
      const content = messages[0].content as { text: string };
      expect(content.text).toMatch(/Aqui está sua rolada: \d+ 🎲/);
    });

    it('should return result between 1 and 20', async () => {
      const data = GroupCommandData.build({ text: ', d20' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      const match = content.text.match(/: (\d+)/);
      expect(match).not.toBeNull();
      const roll = parseInt(match![1], 10);
      expect(roll).toBeGreaterThanOrEqual(1);
      expect(roll).toBeLessThanOrEqual(20);
    });

    it('should return random values', async () => {
      const data = GroupCommandData.build({ text: ', d20' });
      const results = new Set<number>();

      for (let i = 0; i < 100; i++) {
        const messages = await command.run(data);
        const content = messages[0].content as { text: string };
        const match = content.text.match(/: (\d+)/);
        results.add(parseInt(match![1], 10));
      }

      expect(results.size).toBeGreaterThan(1);
    });

    it('should work in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', d20' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', d20', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', d20' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });
  });
});
