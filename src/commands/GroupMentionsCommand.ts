import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { MongoClient } from 'mongodb';

type GroupsDoc = { _id: string; groups: Array<{ name: string; participants: string[] }> };

export default class GroupMentionsCommand {
  static identifier: string = '^\\s*\\,\\s*grupo\\s*';
  static client = new MongoClient(process.env.MONGODB_URI!);

  static async run(data: CommandData): Promise<void> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Burro burro! Você só pode marcar alguém em um grupo! 🤦‍♂️` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
    const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
    const rest_command = data.text.replace(/\s*,\s*grupo\s*/, '');

    const has_function = functions.some((func) => new RegExp(func, 'i').test(rest_command));
    if (!has_function) {
      await this.mention(data, rest_command);
      return;
    }

    for (const func of functions) {
      if (new RegExp(func, 'i').test(rest_command)) {
        await (
          this as unknown as Record<string, (data: CommandData, rest: string) => Promise<void>>
        )[func](data, rest_command.replace(func, '').replace(/\n/g, '').trim());
      }
    }
  }

  static async is_valid_group_name(data: CommandData, group_name: string): Promise<boolean> {
    if (group_name?.length > 15) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `O nome do grupo é desse tamanho! ✋    🤚` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return false;
    }
    const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
    if (functions.some((func) => new RegExp(func, 'i').test(group_name))) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `O nome do grupo não pode ser um comando!` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return false;
    }
    if (group_name.match(/\s/)) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `O nome do grupo não pode ter espaço!` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return false;
    }
    return true;
  }

  static async create(data: CommandData, rest_command: string): Promise<void> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s*@\d+\s*/g, '');
    if (group_name?.length == 0) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Cadê o nome do grupo? 🤔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
    if (!(await this.is_valid_group_name(data, group_name))) {
      return;
    }

    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const has_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': group_name,
      });
      if (has_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Já existe um grupo com o nome *${group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const mentioneds = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
      const has_groups = await collection.findOne({ _id: data.key.remoteJid! });
      if (!has_groups) {
        await collection.insertOne({
          _id: data.key.remoteJid!,
          groups: [{ name: group_name, participants: [sender_id as string, ...mentioneds] }],
        });
      } else {
        await collection.updateOne(
          { _id: data.key.remoteJid! },
          {
            $push: {
              groups: { name: group_name, participants: [sender_id as string, ...mentioneds] },
            },
          },
        );
      }
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Grupo *${group_name}* criado com sucesso! 🎉` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui criar o grupo *${group_name}* 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async rename(data: CommandData, rest_command: string): Promise<void> {
    const has_two_groups = rest_command.match(/[\S]+\s+[\S]+/);
    if (!has_two_groups) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Cadê os nomes dos grupos? 🤔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    const [old_group_name, new_group_name] = rest_command.split(/\s+/);
    if (!(await this.is_valid_group_name(data, new_group_name))) {
      return;
    }
    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const has_old_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': old_group_name,
      });
      if (!has_old_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Não existe um grupo com o nome *${old_group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const has_new_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': new_group_name,
      });
      if (has_new_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Já existe um grupo com o nome *${new_group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      await collection.updateOne(
        { _id: data.key.remoteJid!, 'groups.name': old_group_name },
        { $set: { 'groups.$.name': new_group_name } },
      );
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Grupo *${old_group_name}* renomeado para *${new_group_name}* com sucesso! 🎉` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui renomear o grupo *${old_group_name}* 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async delete(data: CommandData, rest_command: string): Promise<void> {
    const group_name = rest_command;
    if (group_name?.length == 0) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Cadê o nome do grupo? 🤔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const has_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': group_name,
      });
      if (!has_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Não existe um grupo com o nome *${group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      await collection.updateOne(
        { _id: data.key.remoteJid! },
        { $pull: { groups: { name: group_name } } },
      );
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Grupo *${group_name}* deletado com sucesso! 🎉` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui deletar o grupo *${group_name}* 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async list(data: CommandData, rest_command: string): Promise<void> {
    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const response = await collection.findOne({ _id: data.key.remoteJid! });
      const empty_groups = !response || response?.groups?.length == 0;
      if (empty_groups) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Você não tem grupos 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const groups = response!.groups;

      if (rest_command?.length > 0) {
        const group = groups.find((group) => group.name === rest_command);
        if (!group) {
          await Resenhazord2.socket!.sendMessage(
            data.key.remoteJid!,
            { text: `Não existe um grupo com o nome *${rest_command}* 😔` },
            { quoted: data, ephemeralExpiration: data.expiration },
          );
          return;
        }
        const regex = /@lid|@s.whatsapp.net/gi;
        let message = '';
        for (const [index, participant_id] of group.participants.entries()) {
          const participant_number = participant_id.replace(regex, '');
          message += `- ${index + 1}: @${participant_number}\n`;
        }

        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          {
            text: `📜 *${rest_command.toUpperCase()}* 📜\n\n${message}`,
            mentions: group.participants,
          },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const message = groups.map((group) => `- _${group.name}_`).join('\n');
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `📜 *GRUPOS* 📜\n\n${message}` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui listar os grupos 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async add(data: CommandData, rest_command: string): Promise<void> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s*@\d+\s*/g, '');
    if (group_name?.length == 0) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Cadê o nome do grupo? 🤔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const has_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': group_name,
      });
      if (!has_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Não existe um grupo com o nome *${group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const participants = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
      if (participants.length == 0) {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $addToSet: { 'groups.$.participants': sender_id } },
        );
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Você foi adicionado ao grupo *${group_name}* com sucesso! 🎉` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      } else {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $addToSet: { 'groups.$.participants': { $each: participants } } },
        );
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Participantes adicionados ao grupo *${group_name}* com sucesso! 🎉` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
      }
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui adicionar os participantes 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async exit(data: CommandData, rest_command: string): Promise<void> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s+\d+\s*/g, '');
    if (group_name?.length == 0) {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Cadê o nome do grupo? 🤔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }

    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const has_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': group_name,
      });
      if (!has_group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Não existe um grupo com o nome *${group_name}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const has_indexes = new RegExp(/\s+\d+\s*/g, 'i').test(rest_command);
      if (!has_indexes) {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $pull: { 'groups.$.participants': sender_id } },
        );
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Você foi removido do grupo *${group_name}* com sucesso! 🎉` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }
      const indexes = rest_command.match(/\s+(\d+)\s*/g)!.map((index) => parseInt(index.trim()));

      const group = await collection.findOne(
        { _id: data.key.remoteJid!, 'groups.name': group_name },
        { projection: { 'groups.$': 1 } },
      );
      const groupData = group as unknown as { groups: Array<{ participants: string[] }> };
      const participants_to_remove = indexes
        .map((index) => groupData.groups[0].participants[index - 1])
        .filter((participant) => participant !== undefined);

      if (participants_to_remove.length == 0) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Nenhum participante encontrado para os índices fornecidos 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      await collection.updateOne(
        { _id: data.key.remoteJid!, 'groups.name': group_name },
        { $pull: { 'groups.$.participants': { $in: participants_to_remove } } },
      );

      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Participantes removidos do grupo *${group_name}* com sucesso! 🎉` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui remover os participantes 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }

  static async mention(data: CommandData, rest_command: string): Promise<void> {
    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const response = await collection.findOne({ _id: data.key.remoteJid! });
      const empty_groups = !response || response?.groups?.length == 0;
      if (empty_groups) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Você não tem grupos 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }

      const groups = response!.groups;
      const group_name = rest_command.split(/\s+/)[0];
      const text = rest_command.replace(group_name, '').trim();
      const group = groups.find((group) => group.name === group_name);
      if (!group) {
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: `Não existe um grupo com o nome *${rest_command}* 😔` },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }
      const regex = /@lid|@s.whatsapp.net/gi;
      const message = text.length > 0 ? `${text}\n\n` : '';
      const mentions = group.participants.map(
        (participant) => `@${participant.replace(regex, '')}`,
      );
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `${message}${mentions.join(' ')}`, mentions: group.participants },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui marcar os participantes 😔` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }
}
