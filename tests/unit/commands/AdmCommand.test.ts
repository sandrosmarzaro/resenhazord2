import { describe, it, expect, beforeEach, vi } from 'vitest';
import AdmCommand from '../../../src/commands/AdmCommand.js';
import { GroupCommandData, PrivateCommandData, GroupWithBotAdmin } from '../../fixtures/index.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';

describe('AdmCommand', () => {
  let command: AdmCommand;

  beforeEach(() => {
    command = new AdmCommand();
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', adm', true],
      [',adm', true],
      [', ADM', true],
      ['  , adm  ', true],
      ['adm', false],
      ['hello', false],
      [', adm extra', false],
      [', admin', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Burro burro');
      expect(content.text).toContain('grupo');
    });

    it('should fetch admins and mention them with random swearing', async () => {
      const groupMetadata = GroupWithBotAdmin.build({}, { transient: { participantCount: 3 } });
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.text).toContain('Vai se foder administração');
      expect(content.mentions.length).toBeGreaterThan(0);
      for (const mentionId of content.mentions) {
        const isAdmin = groupMetadata.participants.find((p) => p.id === mentionId && p.admin);
        expect(isAdmin).toBeTruthy();
      }
    });

    it('should include @ mentions in text for each admin', async () => {
      const groupMetadata = GroupWithBotAdmin.build({}, { transient: { participantCount: 3 } });
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      const atMentions = content.text.match(/@/g) ?? [];
      const adminCount = groupMetadata.participants.filter((p) => p.admin).length;
      expect(atMentions.length).toBe(adminCount);
    });

    it('should quote the original message', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', adm', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
