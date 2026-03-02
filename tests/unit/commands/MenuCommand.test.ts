import { describe, it, expect, beforeEach, vi } from 'vitest';
import MenuCommand from '../../../src/commands/MenuCommand.js';
import { GroupCommandData, PrivateCommandData } from '../../fixtures/index.js';

vi.mock('../../../../public/messages/menu_message.js', () => ({
  default: 'MOCK_MENU_DEFAULT',
}));
vi.mock('../../../../public/messages/menu_grupo_message.js', () => ({
  default: 'MOCK_MENU_GRUPO',
}));
vi.mock('../../../../public/messages/menu_biblia_message.js', () => ({
  default: 'MOCK_MENU_BIBLIA',
}));

describe('MenuCommand', () => {
  let command: MenuCommand;

  beforeEach(() => {
    command = new MenuCommand();
  });

  describe('matches()', () => {
    it.each([
      [', menu', true],
      [',menu', true],
      [', MENU', true],
      [', menu grupo', true],
      [', menu bíblia', true],
      [', menu biblia', true],
      [', menu dm', true],
      [', menu grupo dm', true],
      ['  , menu  ', true],
      ['menu', false],
      ['hello', false],
      [', menu foo', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return default menu', async () => {
      const data = GroupCommandData.build({ text: ', menu' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
      const content = messages[0].content as { text: string };
      expect(content.text).toBeDefined();
    });

    it('should return grupo menu when grupo keyword is used', async () => {
      const data = GroupCommandData.build({ text: ', menu grupo' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toBeDefined();
    });

    it('should return biblia menu when biblia keyword is used', async () => {
      const data = GroupCommandData.build({ text: ', menu biblia' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toBeDefined();
    });

    it('should send to DM when dm flag is active in group', async () => {
      const data = GroupCommandData.build({ text: ', menu dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.participant);
    });

    it('should not change jid when dm flag is active in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', menu dm' });

      const messages = await command.run(data);

      expect(messages[0].jid).toBe(data.key.remoteJid);
    });

    it('should quote the original message', async () => {
      const data = GroupCommandData.build({ text: ', menu' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const data = GroupCommandData.build({ text: ', menu', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
