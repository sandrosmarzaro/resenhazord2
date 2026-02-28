import { describe, it, expect, beforeEach, vi } from 'vitest';
import BanCommand from '../../../src/commands/BanCommand.js';
import {
  GroupCommandData,
  PrivateCommandData,
  GroupWithBotAdmin,
  GroupWithoutBotAdmin,
  MentionCommandData,
} from '../../fixtures/index.js';
import Resenhazord2 from '../../../src/models/Resenhazord2.js';

describe('BanCommand', () => {
  let command: BanCommand;
  const botJid = process.env.RESENHAZORD2_JID!;

  beforeEach(() => {
    command = new BanCommand();
    vi.restoreAllMocks();
  });

  describe('matches()', () => {
    it.each([
      [', ban', true],
      [',ban', true],
      [', BAN', true],
      [', ban @123456789', true],
      [', ban @123456789 @987654321', true],
      ['  , ban  ', true],
      ['ban', false],
      [', ban text', false],
      [', banana', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run()', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', ban' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      expect(messages[0].jid).toBe(data.key.remoteJid);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Burro burro');
      expect(content.text).toContain('grupo');
    });

    it('should return error when bot is not admin', async () => {
      const groupMetadata = GroupWithoutBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
      } as unknown as typeof Resenhazord2.socket);

      const data = GroupCommandData.build({ text: ', ban' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('não sou admin');
    });

    it('should randomly ban a participant when no mention provided', async () => {
      const groupMetadata = GroupWithBotAdmin.build({}, { transient: { participantCount: 3 } });
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);
      vi.spyOn(Math, 'random').mockReturnValueOnce(0.8).mockReturnValueOnce(0);

      const data = GroupCommandData.build({ text: ', ban' });

      const messages = await command.run(data);

      expect(messages.length).toBeGreaterThanOrEqual(1);
      expect(groupParticipantsUpdate).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Se fudeu');
    });

    it('should not ban the bot itself when randomly selecting', async () => {
      const groupMetadata = GroupWithBotAdmin.build({}, { transient: { participantCount: 3 } });
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);
      vi.spyOn(Math, 'random').mockReturnValueOnce(0.8).mockReturnValueOnce(0);

      const data = GroupCommandData.build({ text: ', ban' });

      await command.run(data);

      const calls = groupParticipantsUpdate.mock.calls;
      for (const call of calls) {
        expect(call[1]).not.toContain(botJid);
      }
    });

    it('should ban mentioned participants when mentions provided', async () => {
      const targetJid = '5511999999999@s.whatsapp.net';
      const groupMetadata = GroupWithBotAdmin.build();
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);

      const data = MentionCommandData([targetJid]).build({ text: ', ban @5511999999999' });

      const messages = await command.run(data);

      expect(groupParticipantsUpdate).toHaveBeenCalledWith(
        data.key.remoteJid,
        [targetJid],
        'remove',
      );
      expect(messages.length).toBe(1);
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.mentions).toContain(targetJid);
    });

    it('should not ban the bot even when explicitly mentioned', async () => {
      const groupMetadata = GroupWithBotAdmin.build();
      const groupParticipantsUpdate = vi.fn().mockResolvedValue(undefined);
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        groupParticipantsUpdate,
      } as unknown as typeof Resenhazord2.socket);

      const data = MentionCommandData([botJid]).build({ text: `, ban @${botJid}` });

      const messages = await command.run(data);

      expect(groupParticipantsUpdate).not.toHaveBeenCalled();
      expect(messages).toHaveLength(0);
    });

    it('should quote the original message', async () => {
      const targetJid = '5511999999999@s.whatsapp.net';
      const groupMetadata = GroupWithBotAdmin.build();
      vi.spyOn(Resenhazord2, 'socket', 'get').mockReturnValue({
        groupMetadata: vi.fn().mockResolvedValue(groupMetadata),
        groupParticipantsUpdate: vi.fn().mockResolvedValue(undefined),
      } as unknown as typeof Resenhazord2.socket);

      const data = MentionCommandData([targetJid]).build({ text: ', ban @5511999999999' });

      const messages = await command.run(data);

      expect(messages[0].options?.quoted).toBe(data);
    });
  });
});
