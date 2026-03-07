import MongoDBConnection from '../infra/MongoDBConnection.js';

type GroupsDoc = { _id: string; groups: Array<GroupEntry> };

export type GroupEntry = { name: string; participants: string[] };
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export default class GroupMentionsService {
  private async getCollection() {
    return MongoDBConnection.getCollection<GroupsDoc>('groups_mentions');
  }

  async create(
    chatJid: string,
    senderJid: string,
    groupName: string,
    mentioned: string[],
  ): Promise<Result<{ groupName: string }>> {
    try {
      const collection = await this.getCollection();

      const hasGroup = await collection.findOne({ _id: chatJid, 'groups.name': groupName });
      if (hasGroup) {
        return { ok: false, message: `Já existe um grupo com o nome *${groupName}* 😔` };
      }

      const participants = [senderJid, ...mentioned];
      const hasChatDoc = await collection.findOne({ _id: chatJid });
      if (!hasChatDoc) {
        await collection.insertOne({ _id: chatJid, groups: [{ name: groupName, participants }] });
      } else {
        await collection.updateOne(
          { _id: chatJid },
          { $push: { groups: { name: groupName, participants } } },
        );
      }
      return { ok: true, data: { groupName } };
    } catch {
      return { ok: false, message: `Não consegui criar o grupo *${groupName}* 😔` };
    }
  }

  async rename(
    chatJid: string,
    oldName: string,
    newName: string,
  ): Promise<Result<{ oldName: string; newName: string }>> {
    try {
      const collection = await this.getCollection();

      const hasOldGroup = await collection.findOne({ _id: chatJid, 'groups.name': oldName });
      if (!hasOldGroup) {
        return { ok: false, message: `Não existe um grupo com o nome *${oldName}* 😔` };
      }

      const hasNewGroup = await collection.findOne({ _id: chatJid, 'groups.name': newName });
      if (hasNewGroup) {
        return { ok: false, message: `Já existe um grupo com o nome *${newName}* 😔` };
      }

      await collection.updateOne(
        { _id: chatJid, 'groups.name': oldName },
        { $set: { 'groups.$.name': newName } },
      );
      return { ok: true, data: { oldName, newName } };
    } catch {
      return { ok: false, message: `Não consegui renomear o grupo *${oldName}* 😔` };
    }
  }

  async delete(chatJid: string, groupName: string): Promise<Result<{ groupName: string }>> {
    try {
      const collection = await this.getCollection();

      const hasGroup = await collection.findOne({ _id: chatJid, 'groups.name': groupName });
      if (!hasGroup) {
        return { ok: false, message: `Não existe um grupo com o nome *${groupName}* 😔` };
      }

      await collection.updateOne({ _id: chatJid }, { $pull: { groups: { name: groupName } } });
      return { ok: true, data: { groupName } };
    } catch {
      return { ok: false, message: `Não consegui deletar o grupo *${groupName}* 😔` };
    }
  }

  async listAll(chatJid: string): Promise<Result<{ groups: GroupEntry[] }>> {
    try {
      const collection = await this.getCollection();
      const response = await collection.findOne({ _id: chatJid });
      if (!response || response.groups.length === 0) {
        return { ok: false, message: `Você não tem grupos 😔` };
      }
      return { ok: true, data: { groups: response.groups } };
    } catch {
      return { ok: false, message: `Não consegui listar os grupos 😔` };
    }
  }

  async listOne(chatJid: string, groupName: string): Promise<Result<GroupEntry>> {
    try {
      const collection = await this.getCollection();
      const response = await collection.findOne({ _id: chatJid });
      if (!response || response.groups.length === 0) {
        return { ok: false, message: `Você não tem grupos 😔` };
      }
      const group = response.groups.find((g) => g.name === groupName);
      if (!group) {
        return { ok: false, message: `Não existe um grupo com o nome *${groupName}* 😔` };
      }
      return { ok: true, data: { name: group.name, participants: group.participants } };
    } catch {
      return { ok: false, message: `Não consegui listar os grupos 😔` };
    }
  }

  async add(
    chatJid: string,
    groupName: string,
    senderJid: string,
    participants: string[],
  ): Promise<Result<{ groupName: string; selfOnly: boolean }>> {
    try {
      const collection = await this.getCollection();

      const hasGroup = await collection.findOne({ _id: chatJid, 'groups.name': groupName });
      if (!hasGroup) {
        return { ok: false, message: `Não existe um grupo com o nome *${groupName}* 😔` };
      }

      if (participants.length === 0) {
        await collection.updateOne(
          { _id: chatJid, 'groups.name': groupName },
          { $addToSet: { 'groups.$.participants': senderJid } },
        );
        return { ok: true, data: { groupName, selfOnly: true } };
      }

      await collection.updateOne(
        { _id: chatJid, 'groups.name': groupName },
        { $addToSet: { 'groups.$.participants': { $each: participants } } },
      );
      return { ok: true, data: { groupName, selfOnly: false } };
    } catch {
      return { ok: false, message: `Não consegui adicionar os participantes 😔` };
    }
  }

  async exit(
    chatJid: string,
    groupName: string,
    senderJid: string,
    indices: number[],
  ): Promise<Result<{ groupName: string; selfOnly: boolean }>> {
    try {
      const collection = await this.getCollection();

      const hasGroup = await collection.findOne({ _id: chatJid, 'groups.name': groupName });
      if (!hasGroup) {
        return { ok: false, message: `Não existe um grupo com o nome *${groupName}* 😔` };
      }

      if (indices.length === 0) {
        await collection.updateOne(
          { _id: chatJid, 'groups.name': groupName },
          { $pull: { 'groups.$.participants': senderJid } },
        );
        return { ok: true, data: { groupName, selfOnly: true } };
      }

      const group = await collection.findOne(
        { _id: chatJid, 'groups.name': groupName },
        { projection: { 'groups.$': 1 } },
      );
      const groupData = group as unknown as { groups: Array<{ participants: string[] }> };
      const toRemove = indices
        .map((i) => groupData.groups[0].participants[i - 1])
        .filter((p): p is string => p !== undefined);

      if (toRemove.length === 0) {
        return {
          ok: false,
          message: `Nenhum participante encontrado para os índices fornecidos 😔`,
        };
      }

      await collection.updateOne(
        { _id: chatJid, 'groups.name': groupName },
        { $pull: { 'groups.$.participants': { $in: toRemove } } },
      );
      return { ok: true, data: { groupName, selfOnly: false } };
    } catch {
      return { ok: false, message: `Não consegui remover os participantes 😔` };
    }
  }

  async mention(chatJid: string, groupName: string): Promise<Result<{ participants: string[] }>> {
    try {
      const collection = await this.getCollection();
      const response = await collection.findOne({ _id: chatJid });
      if (!response || response.groups.length === 0) {
        return { ok: false, message: `Você não tem grupos 😔` };
      }
      const group = response.groups.find((g) => g.name === groupName);
      if (!group) {
        return { ok: false, message: `Não existe um grupo com o nome *${groupName}* 😔` };
      }
      return { ok: true, data: { participants: group.participants } };
    } catch {
      return { ok: false, message: `Não consegui marcar os participantes 😔` };
    }
  }
}
