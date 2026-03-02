import { describe, it, expect, beforeEach, vi } from 'vitest';
import GroupMentionsCommand from '../../../src/commands/GroupMentionsCommand.js';
import { GroupCommandData, PrivateCommandData, MentionCommandData } from '../../fixtures/index.js';
import MongoDBConnection from '../../../src/infra/MongoDBConnection.js';

describe('GroupMentionsCommand', () => {
  let command: GroupMentionsCommand;

  const mockCollection = () => {
    const col = {
      findOne: vi.fn().mockResolvedValue(null),
      insertOne: vi.fn().mockResolvedValue({ insertedId: 'test' }),
      updateOne: vi.fn().mockResolvedValue({ modifiedCount: 1 }),
    };
    vi.spyOn(MongoDBConnection, 'getCollection').mockResolvedValue(col as never);
    return col;
  };

  beforeEach(() => {
    command = new GroupMentionsCommand();
    vi.restoreAllMocks();
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
      expect(content.text).toContain('Burro burro');
      expect(content.text).toContain('grupo');
    });
  });

  describe('run() - create', () => {
    it('should create a new group when chat doc does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce(null);
      const data = GroupCommandData.build({ text: ', grupo create testgroup' });

      const messages = await command.run(data);

      expect(col.insertOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('testgroup');
      expect(content.text).toContain('criado com sucesso');
    });

    it('should push to existing chat doc when it exists', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce({ _id: 'chat', groups: [] });
      const data = GroupCommandData.build({ text: ', grupo create newgroup' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('newgroup');
      expect(content.text).toContain('criado com sucesso');
    });

    it('should return error when group already exists', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'dup' }] });
      const data = GroupCommandData.build({ text: ', grupo create dup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Já existe');
    });
  });

  describe('run() - add', () => {
    it('should add sender when no mentions', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });
      const data = GroupCommandData.build({ text: ', grupo add mygroup' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Você foi adicionado');
    });

    it('should add mentioned participants', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });
      const mentionedJid = '5511999999999@s.whatsapp.net';
      const data = MentionCommandData([mentionedJid]).build({
        text: ', grupo add mygroup @5511999999999',
      });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Participantes adicionados');
    });
  });

  describe('run() - exit', () => {
    it('should remove sender when no index provided', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });
      const data = GroupCommandData.build({ text: ', grupo exit mygroup' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Você foi removido');
    });

    it('should remove participant by index', async () => {
      const col = mockCollection();
      col.findOne
        .mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'mygroup' }] })
        .mockResolvedValueOnce({
          groups: [{ participants: ['user1@s.whatsapp.net', 'user2@s.whatsapp.net'] }],
        });
      const data = GroupCommandData.build({ text: ', grupo exit mygroup 1' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Participantes removidos');
    });
  });

  describe('run() - delete', () => {
    it('should delete an existing group', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });
      const data = GroupCommandData.build({ text: ', grupo delete mygroup' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('deletado com sucesso');
    });

    it('should return error when group does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);
      const data = GroupCommandData.build({ text: ', grupo delete nogroup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não existe');
    });
  });

  describe('run() - rename', () => {
    it('should rename an existing group', async () => {
      const col = mockCollection();
      col.findOne
        .mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'old' }] })
        .mockResolvedValueOnce(null);
      const data = GroupCommandData.build({ text: ', grupo rename old new' });

      const messages = await command.run(data);

      expect(col.updateOne).toHaveBeenCalled();
      const content = messages[0].content as { text: string };
      expect(content.text).toContain('renomeado');
    });

    it('should return error when missing group names', async () => {
      mockCollection();
      const data = GroupCommandData.build({ text: ', grupo rename' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('nomes dos grupos');
    });
  });

  describe('run() - list', () => {
    it('should list all groups', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'group1' }, { name: 'group2' }],
      });
      const data = GroupCommandData.build({ text: ', grupo list' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('GRUPOS');
      expect(content.text).toContain('group1');
      expect(content.text).toContain('group2');
    });

    it('should list specific group with participants', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'mygroup', participants: ['5511900000000@s.whatsapp.net'] }],
      });
      const data = GroupCommandData.build({ text: ', grupo list mygroup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.text).toContain('MYGROUP');
      expect(content.mentions).toContain('5511900000000@s.whatsapp.net');
    });

    it('should return error when no groups exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);
      const data = GroupCommandData.build({ text: ', grupo list' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('não tem grupos');
    });
  });

  describe('run() - mention', () => {
    it('should mention all participants in a group', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [
          {
            name: 'devs',
            participants: ['5511900000000@s.whatsapp.net', '5511900000001@s.whatsapp.net'],
          },
        ],
      });
      const data = GroupCommandData.build({ text: ', grupo devs' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string; mentions: string[] };
      expect(content.mentions).toHaveLength(2);
      expect(content.text).toContain('@');
    });

    it('should include custom text when provided', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'devs', participants: ['5511900000000@s.whatsapp.net'] }],
      });
      const data = GroupCommandData.build({ text: ', grupo devs hello world' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('hello world');
    });

    it('should return error when group not found', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'other' }],
      });
      const data = GroupCommandData.build({ text: ', grupo nogroup' });

      const messages = await command.run(data);

      const content = messages[0].content as { text: string };
      expect(content.text).toContain('Não existe');
    });
  });
});
