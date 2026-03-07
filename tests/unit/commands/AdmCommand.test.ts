import { describe, it, expect, beforeEach, vi } from 'vitest';
import AdmCommand from '../../../src/commands/AdmCommand.js';
import {
  GroupCommandData,
  PrivateCommandData,
  GroupWithBotAdmin,
  createMockWhatsAppPort,
} from '../../fixtures/index.js';

describe('AdmCommand', () => {
  let command: AdmCommand;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    beforeEach(() => {
      command = new AdmCommand();
    });

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
      command = new AdmCommand();
      const data = PrivateCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('grupo');
    });

    it('should fetch admins and mention them with random swearing', async () => {
      const groupMetadata = GroupWithBotAdmin.build({}, { transient: { participantCount: 3 } });
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AdmCommand(mockWhatsApp);

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
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AdmCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      const atMentions = content.text.match(/@/g) ?? [];
      const adminCount = groupMetadata.participants.filter((p) => p.admin).length;
      expect(atMentions.length).toBe(adminCount);
    });

    it('should quote the original message', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AdmCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', adm' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });

    it('should include ephemeral expiration from data', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AdmCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', adm', expiration: 86400 });

      const messages = await command.run(data);

      expect(messages[0].options?.ephemeralExpiration).toBe(86400);
    });
  });
});
