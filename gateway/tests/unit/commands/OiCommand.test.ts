import { describe, it, expect, beforeEach } from 'vitest';
import OiCommand from '../../../src/commands/OiCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

describe('OiCommand', () => {
  let command: OiCommand;

  beforeEach(() => {
    command = new OiCommand();
  });

  describe('matches()', () => {
    it.each([
      [', oi', true],
      [',oi', true],
      [', OI', true],
      [',OI', true],
      ['  , oi  ', true],
      ['\t,\toi\t', true],
      ['oi', false],
      ['hello', false],
      ['oi,', false],
      [', oi test', false],
      [', oie', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return message mentioning sender in group chat', async () => {
      const data = GroupCommandData.build({ text: ', oi' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
      expect(messages[0].content).toHaveProperty('text');
      expect(messages[0].content).toHaveProperty('mentions');
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.text).toContain('@');
      expect(content.mentions).toContain(data.key.participant);
      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should use remoteJid when no participant (private chat)', async () => {
      const data = PrivateCommandData.build({ text: ', oi' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.mentions).toContain(data.key.remoteJid);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', oi', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
