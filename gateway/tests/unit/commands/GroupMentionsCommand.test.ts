import { describe, it, expect, beforeEach, vi } from 'vitest';
import GroupMentionsCommand from '../../../src/commands/GroupMentionsCommand.js';
import GroupMentionsService from '../../../src/services/GroupMentionsService.js';
import { GroupCommandData, PrivateCommandData, MentionCommandData } from '../../fixtures/index.js';

type MockService = {
  [K in keyof GroupMentionsService]: ReturnType<typeof vi.fn>;
};

describe('GroupMentionsCommand', () => {
  let command: GroupMentionsCommand;
  let service: MockService;

  beforeEach(() => {
    service = {
      create: vi.fn(),
      rename: vi.fn(),
      delete: vi.fn(),
      listAll: vi.fn(),
      listOne: vi.fn(),
      add: vi.fn(),
      exit: vi.fn(),
      mention: vi.fn(),
    };
    command = new GroupMentionsCommand(service as unknown as GroupMentionsService);
  });

  describe('matches()', () => {
    it.each([
      [', grupo', true],
      [',grupo', true],
      [', GRUPO', true],
      [', grupo create test', true],
      [', grupo add test', true],
      [', grupo exit test', true],
      [', grupo delete test', true],
      [', grupo rename old new', true],
      [', grupo list', true],
      [', grupo mygroup', true],
      ['  , grupo  ', true],
      ['grupo', false],
      ['hello', false],
    ])('should return %s for "%s"', (input, expected) => {
      expect(command.matches(input)).toBe(expected);
    });
  });

  describe('run() - private chat error', () => {
    it('should return error message when used in private chat', async () => {
      const data = PrivateCommandData.build({ text: ', grupo list' });

      const messages = await command.run(data);

      expect(messages).toHaveLength(1);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('grupo');
    });
  });

  describe('run() - create', () => {
    it('should return success message when service creates group', async () => {
      service.create.mockResolvedValue({ ok: true, data: { groupName: 'testgroup' } });
      const data = GroupCommandData.build({ text: ', grupo create testgroup' });

      const messages = await command.run(data);

      expect(service.create).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        'testgroup',
        [],
      );
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('testgroup');
      expect(content.text).toContain('criado com sucesso');
    });

    it('should return error message from service', async () => {
      service.create.mockResolvedValue({
        ok: false,
        message: 'Já existe um grupo com o nome *dup* 😔',
      });
      const data = GroupCommandData.build({ text: ', grupo create dup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Já existe');
    });

    it('should return error when no group name provided', async () => {
      const data = GroupCommandData.build({ text: ', grupo create' });

      const messages = await command.run(data);

      expect(service.create).not.toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Cadê o nome do grupo');
    });

    it('should pass mentioned JIDs to service', async () => {
      service.create.mockResolvedValue({ ok: true, data: { groupName: 'mygroup' } });
      const mentionedJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([mentionedJid]).build({
        text: ', grupo create mygroup @5511999999999',
      });

      await command.run(data);

      expect(service.create).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(String),
        'mygroup',
        [mentionedJid],
      );
    });
  });

  describe('run() - rename', () => {
    it('should return success message when service renames group', async () => {
      service.rename.mockResolvedValue({ ok: true, data: { oldName: 'old', newName: 'new' } });
      const data = GroupCommandData.build({ text: ', grupo rename old new' });

      const messages = await command.run(data);

      expect(service.rename).toHaveBeenCalledWith(expect.any(String), 'old', 'new');
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('renomeado');
    });

    it('should return error when missing group names', async () => {
      const data = GroupCommandData.build({ text: ', grupo rename' });

      const messages = await command.run(data);

      expect(service.rename).not.toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('nomes dos grupos');
    });

    it('should return service error message', async () => {
      service.rename.mockResolvedValue({
        ok: false,
        message: 'Não existe um grupo com o nome *old* 😔',
      });
      const data = GroupCommandData.build({ text: ', grupo rename old new' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não existe');
    });
  });

  describe('run() - delete', () => {
    it('should return success message when service deletes group', async () => {
      service.delete.mockResolvedValue({ ok: true, data: { groupName: 'mygroup' } });
      const data = GroupCommandData.build({ text: ', grupo delete mygroup' });

      const messages = await command.run(data);

      expect(service.delete).toHaveBeenCalledWith(expect.any(String), 'mygroup');
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('deletado com sucesso');
    });

    it('should return service error message when group does not exist', async () => {
      service.delete.mockResolvedValue({
        ok: false,
        message: 'Não existe um grupo com o nome *nogroup* 😔',
      });
      const data = GroupCommandData.build({ text: ', grupo delete nogroup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não existe');
    });
  });

  describe('run() - list', () => {
    it('should list all groups when no name provided', async () => {
      service.listAll.mockResolvedValue({
        ok: true,
        data: {
          groups: [
            { name: 'group1', participants: [] },
            { name: 'group2', participants: [] },
          ],
        },
      });
      const data = GroupCommandData.build({ text: ', grupo list' });

      const messages = await command.run(data);

      expect(service.listAll).toHaveBeenCalledWith(expect.any(String));
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('GRUPOS');
      expect(content.text).toContain('group1');
      expect(content.text).toContain('group2');
    });

    it('should list specific group participants when name provided', async () => {
      service.listOne.mockResolvedValue({
        ok: true,
        data: { name: 'mygroup', participants: ['5511900000000@s.whatsapp.net'] },
      });
      const data = GroupCommandData.build({ text: ', grupo list mygroup' });

      const messages = await command.run(data);

      expect(service.listOne).toHaveBeenCalledWith(expect.any(String), 'mygroup');
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.text).toContain('MYGROUP');
      expect(content.mentions).toContain('5511900000000@s.whatsapp.net');
    });

    it('should return error when no groups exist', async () => {
      service.listAll.mockResolvedValue({ ok: false, message: 'Você não tem grupos 😔' });
      const data = GroupCommandData.build({ text: ', grupo list' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('não tem grupos');
    });
  });

  describe('run() - add', () => {
    it('should return self-add message when no mentions', async () => {
      service.add.mockResolvedValue({ ok: true, data: { groupName: 'mygroup', selfOnly: true } });
      const data = GroupCommandData.build({ text: ', grupo add mygroup' });

      const messages = await command.run(data);

      expect(service.add).toHaveBeenCalledWith(
        expect.any(String),
        'mygroup',
        expect.any(String),
        [],
      );
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Você foi adicionado');
    });

    it('should return multi-add message when participants mentioned', async () => {
      service.add.mockResolvedValue({ ok: true, data: { groupName: 'mygroup', selfOnly: false } });
      const mentionedJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([mentionedJid]).build({
        text: ', grupo add mygroup @5511999999999',
      });

      const messages = await command.run(data);

      expect(service.add).toHaveBeenCalledWith(expect.any(String), 'mygroup', expect.any(String), [
        mentionedJid,
      ]);
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Participantes adicionados');
    });
  });

  describe('run() - exit', () => {
    it('should return self-remove message when no index provided', async () => {
      service.exit.mockResolvedValue({ ok: true, data: { groupName: 'mygroup', selfOnly: true } });
      const data = GroupCommandData.build({ text: ', grupo exit mygroup' });

      const messages = await command.run(data);

      expect(service.exit).toHaveBeenCalledWith(
        expect.any(String),
        'mygroup',
        expect.any(String),
        [],
      );
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Você foi removido');
    });

    it('should return multi-remove message when index provided', async () => {
      service.exit.mockResolvedValue({ ok: true, data: { groupName: 'mygroup', selfOnly: false } });
      const data = GroupCommandData.build({ text: ', grupo exit mygroup 1' });

      const messages = await command.run(data);

      expect(service.exit).toHaveBeenCalledWith(
        expect.any(String),
        'mygroup',
        expect.any(String),
        [1],
      );
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Participantes removidos');
    });
  });

  describe('run() - mention', () => {
    it('should mention all participants in a group', async () => {
      service.mention.mockResolvedValue({
        ok: true,
        data: { participants: ['5511900000000@s.whatsapp.net', '5511900000001@s.whatsapp.net'] },
      });
      const data = GroupCommandData.build({ text: ', grupo devs' });

      const messages = await command.run(data);

      expect(service.mention).toHaveBeenCalledWith(expect.any(String), 'devs');
      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.mentions).toHaveLength(2);
      expect(content.text).toContain('@');
    });

    it('should include custom text when provided', async () => {
      service.mention.mockResolvedValue({
        ok: true,
        data: { participants: ['5511900000000@s.whatsapp.net'] },
      });
      const data = GroupCommandData.build({ text: ', grupo devs hello world' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('hello world');
    });

    it('should return service error when group not found', async () => {
      service.mention.mockResolvedValue({
        ok: false,
        message: 'Não existe um grupo com o nome *nogroup* 😔',
      });
      const data = GroupCommandData.build({ text: ', grupo nogroup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não existe');
    });
  });
});
