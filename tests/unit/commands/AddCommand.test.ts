import { describe, it, expect, beforeEach, vi } from 'vitest';
import AddCommand from '../../../src/commands/AddCommand.js';
import {
  GroupCommandData,
  PrivateCommandData,
  GroupWithBotAdmin,
  GroupWithoutBotAdmin,
} from '../../fixtures/index.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';

describe('AddCommand', () => {
  let command: AddCommand;

  beforeEach(() => {
    command = new AddCommand();
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', add', true],
      [',add', true],
      [', ADD', true],
      [', add 11999999999', true],
      ['  , add  ', true],
      ['add', false],
      ['hello', false],
      [', add text', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', add' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('grupo');
    });

    it('should return error when bot is not admin', async () => {
      const groupMetadata = GroupWithoutBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', add' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('não sou admin');
    });

    it('should generate random phone when no phone provided', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const onWhatsApp = vi
        .fn()
        .mockResolvedValue([{ exists: true, jid: '5511999999999@s.whatsapp.net' }]);
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        onWhatsApp,
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', add' });

      const messages = await command.run(data);

      expect(onWhatsApp).toHaveBeenCalled();
      expect(messages).toHaveLength(0);
    });

    it('should add specific phone with valid DDD', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const onWhatsApp = vi
        .fn()
        .mockResolvedValue([{ exists: true, jid: '5511999999999@s.whatsapp.net' }]);
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        onWhatsApp,
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', add 11999999999' });

      const messages = await command.run(data);

      expect(groupParticipantsUpdate).toHaveBeenCalled();
      expect(messages).toHaveLength(0);
    });

    it('should return error for invalid DDD', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', add 00999999999' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('DDD');
    });

    it('should warn when phone is too long', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const onWhatsApp = vi
        .fn()
        .mockResolvedValue([{ exists: true, jid: '5511999999999@s.whatsapp.net' }]);
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        onWhatsApp,
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', add 119999999999999' });

      const messages = await command.run(data);

      expect(messages.length).toBeGreaterThanOrEqual(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('tamanho');
    });
  });
});
