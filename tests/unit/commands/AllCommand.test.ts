import { describe, it, expect, beforeEach, vi } from 'vitest';
import AllCommand from '../../../src/commands/AllCommand.js';
import {
  GroupCommandData,
  PrivateCommandData,
  GroupWithBotAdmin,
  createMockWhatsAppPort,
} from '../../fixtures/index.js';

describe('AllCommand', () => {
  let command: AllCommand;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    beforeEach(() => {
      command = new AllCommand();
    });

    it.each([
      [', all', true],
      [',all', true],
      [', ALL', true],
      [',ALL', true],
      ['  , all  ', true],
      [', all some message', true],
      [', all\nmultiline', true],
      ['all', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when used in private chat', async () => {
      command = new AllCommand();
      const data = PrivateCommandData.build({ text: ', all' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('grupo');
    });

    it('should mention all participants in group', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AllCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', all' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.mentions).toHaveLength(groupMetadata.participants.length);
      for (const participant of groupMetadata.participants) {
        expect(content.mentions).toContain(participant.id);
      }
    });

    it('should include custom message when provided', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AllCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', all Attention everyone!' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Attention everyone!');
    });

    it('should include @mentions in the text for each participant', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AllCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', all' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      const atMentions = content.text.match(/@/g) ?? [];
      expect(atMentions.length).toBe(groupMetadata.participants.length);
    });

    it('should quote the original message', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const mockWhatsApp = createMockWhatsAppPort({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      });
      command = new AllCommand(mockWhatsApp);

      const data = GroupCommandData.build({ text: ', all' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });
  });
});
