import { describe, it, expect, beforeEach, vi } from 'vitest';
import GroupMentionsService from '../../../src/services/GroupMentionsService.js';
import MongoDBConnection from '../../../src/infra/MongoDBConnection.js';

describe('GroupMentionsService', () => {
  let service: GroupMentionsService;

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
    service = new GroupMentionsService();
    vi.restoreAllMocks();
  });

  describe('create()', () => {
    it('should insert new doc when chat does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce(null);

      const result = await service.create('chat@g.us', 'sender@s.whatsapp.net', 'mygroup', []);

      expect(result.ok).toBe(true);
      expect(col.insertOne).toHaveBeenCalled();
      if (result.ok) expect(result.data.groupName).toBe('mygroup');
    });

    it('should push to existing doc when chat already exists', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce({ _id: 'chat', groups: [] });

      const result = await service.create('chat@g.us', 'sender@s.whatsapp.net', 'mygroup', []);

      expect(result.ok).toBe(true);
      expect(col.updateOne).toHaveBeenCalled();
    });

    it('should include mentioned JIDs in participants', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null).mockResolvedValueOnce(null);
      const mentioned = ['user1@s.whatsapp.net', 'user2@s.whatsapp.net'];

      await service.create('chat@g.us', 'sender@s.whatsapp.net', 'mygroup', mentioned);

      const insertArg = col.insertOne.mock.calls[0][0];
      expect(insertArg.groups[0].participants).toContain('user1@s.whatsapp.net');
      expect(insertArg.groups[0].participants).toContain('sender@s.whatsapp.net');
    });

    it('should return error when group name already exists', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'mygroup' }] });

      const result = await service.create('chat@g.us', 'sender@s.whatsapp.net', 'mygroup', []);

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Já existe');
    });
  });

  describe('rename()', () => {
    it('should rename the group', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'old' }] });
      col.findOne.mockResolvedValueOnce(null);

      const result = await service.rename('chat@g.us', 'old', 'new');

      expect(result.ok).toBe(true);
      expect(col.updateOne).toHaveBeenCalled();
      if (result.ok) {
        expect(result.data.oldName).toBe('old');
        expect(result.data.newName).toBe('new');
      }
    });

    it('should return error when old group does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce(null);

      const result = await service.rename('chat@g.us', 'old', 'new');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Não existe');
    });

    it('should return error when new name is already taken', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'old' }] });
      col.findOne.mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'new' }] });

      const result = await service.rename('chat@g.us', 'old', 'new');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Já existe');
    });
  });

  describe('delete()', () => {
    it('should delete the group', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });

      const result = await service.delete('chat@g.us', 'mygroup');

      expect(result.ok).toBe(true);
      expect(col.updateOne).toHaveBeenCalledWith(
        { _id: 'chat@g.us' },
        { $pull: { groups: { name: 'mygroup' } } },
      );
    });

    it('should return error when group does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);

      const result = await service.delete('chat@g.us', 'nogroup');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Não existe');
    });
  });

  describe('listAll()', () => {
    it('should return all groups', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [
          { name: 'g1', participants: [] },
          { name: 'g2', participants: [] },
        ],
      });

      const result = await service.listAll('chat@g.us');

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.groups).toHaveLength(2);
    });

    it('should return error when no groups exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);

      const result = await service.listAll('chat@g.us');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('não tem grupos');
    });

    it('should return error when groups array is empty', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [] });

      const result = await service.listAll('chat@g.us');

      expect(result.ok).toBe(false);
    });
  });

  describe('listOne()', () => {
    it('should return the specific group', async () => {
      const col = mockCollection();
      const participants = ['user@s.whatsapp.net'];
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'mygroup', participants }],
      });

      const result = await service.listOne('chat@g.us', 'mygroup');

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data.name).toBe('mygroup');
        expect(result.data.participants).toEqual(participants);
      }
    });

    it('should return error when group not found', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'other', participants: [] }] });

      const result = await service.listOne('chat@g.us', 'notfound');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Não existe');
    });
  });

  describe('add()', () => {
    it('should add sender when no participants provided', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });

      const result = await service.add('chat@g.us', 'mygroup', 'sender@s.whatsapp.net', []);

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.selfOnly).toBe(true);
      expect(col.updateOne).toHaveBeenCalledWith(
        expect.objectContaining({ 'groups.name': 'mygroup' }),
        { $addToSet: { 'groups.$.participants': 'sender@s.whatsapp.net' } },
      );
    });

    it('should add all participants when list is provided', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });
      const participants = ['user1@s.whatsapp.net', 'user2@s.whatsapp.net'];

      const result = await service.add(
        'chat@g.us',
        'mygroup',
        'sender@s.whatsapp.net',
        participants,
      );

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.selfOnly).toBe(false);
      expect(col.updateOne).toHaveBeenCalledWith(
        expect.objectContaining({ 'groups.name': 'mygroup' }),
        { $addToSet: { 'groups.$.participants': { $each: participants } } },
      );
    });

    it('should return error when group does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);

      const result = await service.add('chat@g.us', 'nogroup', 'sender@s.whatsapp.net', []);

      expect(result.ok).toBe(false);
    });
  });

  describe('exit()', () => {
    it('should remove sender when no indices provided', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'mygroup' }] });

      const result = await service.exit('chat@g.us', 'mygroup', 'sender@s.whatsapp.net', []);

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.selfOnly).toBe(true);
      expect(col.updateOne).toHaveBeenCalledWith(
        expect.objectContaining({ 'groups.name': 'mygroup' }),
        { $pull: { 'groups.$.participants': 'sender@s.whatsapp.net' } },
      );
    });

    it('should remove participants by index when indices provided', async () => {
      const col = mockCollection();
      col.findOne
        .mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'mygroup' }] })
        .mockResolvedValueOnce({
          groups: [{ participants: ['user1@s.whatsapp.net', 'user2@s.whatsapp.net'] }],
        });

      const result = await service.exit('chat@g.us', 'mygroup', 'sender@s.whatsapp.net', [1]);

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.selfOnly).toBe(false);
      expect(col.updateOne).toHaveBeenCalledWith(
        expect.objectContaining({ 'groups.name': 'mygroup' }),
        { $pull: { 'groups.$.participants': { $in: ['user1@s.whatsapp.net'] } } },
      );
    });

    it('should return error when indices point to no participants', async () => {
      const col = mockCollection();
      col.findOne
        .mockResolvedValueOnce({ _id: 'chat', groups: [{ name: 'mygroup' }] })
        .mockResolvedValueOnce({ groups: [{ participants: [] }] });

      const result = await service.exit('chat@g.us', 'mygroup', 'sender@s.whatsapp.net', [99]);

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('índices');
    });

    it('should return error when group does not exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);

      const result = await service.exit('chat@g.us', 'nogroup', 'sender@s.whatsapp.net', []);

      expect(result.ok).toBe(false);
    });
  });

  describe('mention()', () => {
    it('should return participants of the group', async () => {
      const col = mockCollection();
      const participants = ['user1@s.whatsapp.net', 'user2@s.whatsapp.net'];
      col.findOne.mockResolvedValue({
        _id: 'chat',
        groups: [{ name: 'devs', participants }],
      });

      const result = await service.mention('chat@g.us', 'devs');

      expect(result.ok).toBe(true);
      if (result.ok) expect(result.data.participants).toEqual(participants);
    });

    it('should return error when no groups exist', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue(null);

      const result = await service.mention('chat@g.us', 'devs');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('não tem grupos');
    });

    it('should return error when specific group not found', async () => {
      const col = mockCollection();
      col.findOne.mockResolvedValue({ _id: 'chat', groups: [{ name: 'other', participants: [] }] });

      const result = await service.mention('chat@g.us', 'devs');

      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.message).toContain('Não existe');
    });
  });
});
