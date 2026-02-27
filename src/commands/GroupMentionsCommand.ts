import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { MongoClient } from 'mongodb';

type GroupsDoc = { _id: string; groups: Array<{ name: string; participants: string[] }> };

export default class GroupMentionsCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*grupo\\s*';
  readonly menuDescription = 'Comando complexo. Use *,menu grupo* para detalhes.';

  private client = new MongoClient(process.env.MONGODB_URI!);

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode marcar alguém em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
    const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
    const rest_command = data.text.replace(/\s*,\s*grupo\s*/, '');

    const has_function = functions.some((func) => new RegExp(func, 'i').test(rest_command));
    if (!has_function) {
      return await this.mention(data, rest_command);
    }

    for (const func of functions) {
      if (new RegExp(func, 'i').test(rest_command)) {
        return await (
          this as unknown as Record<string, (data: CommandData, rest: string) => Promise<Message[]>>
        )[func](data, rest_command.replace(func, '').replace(/\n/g, '').trim());
      }
    }
    return [];
  }

  private is_valid_group_name(data: CommandData, group_name: string): Message | null {
    if (group_name?.length > 15) {
      return {
        jid: data.key.remoteJid!,
        content: { text: `O nome do grupo é desse tamanho! ✋    🤚` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      };
    }
    const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
    if (functions.some((func) => new RegExp(func, 'i').test(group_name))) {
      return {
        jid: data.key.remoteJid!,
        content: { text: `O nome do grupo não pode ser um comando!` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      };
    }
    if (group_name.match(/\s/)) {
      return {
        jid: data.key.remoteJid!,
        content: { text: `O nome do grupo não pode ter espaço!` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      };
    }
    return null;
  }

  private async create(data: CommandData, rest_command: string): Promise<Message[]> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s*@\d+\s*/g, '');
    if (group_name?.length == 0) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Cadê o nome do grupo? 🤔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
    const validationError = this.is_valid_group_name(data, group_name);
    if (validationError) {
      return [validationError];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Já existe um grupo com o nome *${group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
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
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Grupo *${group_name}* criado com sucesso! 🎉` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui criar o grupo *${group_name}* 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async rename(data: CommandData, rest_command: string): Promise<Message[]> {
    const has_two_groups = rest_command.match(/[\S]+\s+[\S]+/);
    if (!has_two_groups) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Cadê os nomes dos grupos? 🤔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const [old_group_name, new_group_name] = rest_command.split(/\s+/);
    const validationError = this.is_valid_group_name(data, new_group_name);
    if (validationError) {
      return [validationError];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Não existe um grupo com o nome *${old_group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const has_new_group = await collection.findOne({
        _id: data.key.remoteJid!,
        'groups.name': new_group_name,
      });
      if (has_new_group) {
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Já existe um grupo com o nome *${new_group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      await collection.updateOne(
        { _id: data.key.remoteJid!, 'groups.name': old_group_name },
        { $set: { 'groups.$.name': new_group_name } },
      );
      return [
        {
          jid: data.key.remoteJid!,
          content: {
            text: `Grupo *${old_group_name}* renomeado para *${new_group_name}* com sucesso! 🎉`,
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui renomear o grupo *${old_group_name}* 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async delete(data: CommandData, rest_command: string): Promise<Message[]> {
    const group_name = rest_command;
    if (group_name?.length == 0) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Cadê o nome do grupo? 🤔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Não existe um grupo com o nome *${group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      await collection.updateOne(
        { _id: data.key.remoteJid! },
        { $pull: { groups: { name: group_name } } },
      );
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Grupo *${group_name}* deletado com sucesso! 🎉` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui deletar o grupo *${group_name}* 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async list(data: CommandData, rest_command: string): Promise<Message[]> {
    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const response = await collection.findOne({ _id: data.key.remoteJid! });
      const empty_groups = !response || response?.groups?.length == 0;
      if (empty_groups) {
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Você não tem grupos 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const groups = response!.groups;

      if (rest_command?.length > 0) {
        const group = groups.find((group) => group.name === rest_command);
        if (!group) {
          return [
            {
              jid: data.key.remoteJid!,
              content: { text: `Não existe um grupo com o nome *${rest_command}* 😔` },
              options: { quoted: data, ephemeralExpiration: data.expiration },
            },
          ];
        }
        const regex = /@lid|@s.whatsapp.net/gi;
        let message = '';
        for (const [index, participant_id] of group.participants.entries()) {
          const participant_number = participant_id.replace(regex, '');
          message += `- ${index + 1}: @${participant_number}\n`;
        }

        return [
          {
            jid: data.key.remoteJid!,
            content: {
              text: `📜 *${rest_command.toUpperCase()}* 📜\n\n${message}`,
              mentions: group.participants,
            },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const message = groups.map((group) => `- _${group.name}_`).join('\n');
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `📜 *GRUPOS* 📜\n\n${message}` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui listar os grupos 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async add(data: CommandData, rest_command: string): Promise<Message[]> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s*@\d+\s*/g, '');
    if (group_name?.length == 0) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Cadê o nome do grupo? 🤔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Não existe um grupo com o nome *${group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const participants = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
      if (participants.length == 0) {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $addToSet: { 'groups.$.participants': sender_id } },
        );
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Você foi adicionado ao grupo *${group_name}* com sucesso! 🎉` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      } else {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $addToSet: { 'groups.$.participants': { $each: participants } } },
        );
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Participantes adicionados ao grupo *${group_name}* com sucesso! 🎉` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui adicionar os participantes 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async exit(data: CommandData, rest_command: string): Promise<Message[]> {
    const sender_id = data.key.participant ?? data.key.remoteJid;

    const group_name = rest_command.replace(/\s+\d+\s*/g, '');
    if (group_name?.length == 0) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Cadê o nome do grupo? 🤔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Não existe um grupo com o nome *${group_name}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const has_indexes = new RegExp(/\s+\d+\s*/g, 'i').test(rest_command);
      if (!has_indexes) {
        await collection.updateOne(
          { _id: data.key.remoteJid!, 'groups.name': group_name },
          { $pull: { 'groups.$.participants': sender_id } },
        );
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Você foi removido do grupo *${group_name}* com sucesso! 🎉` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
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
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Nenhum participante encontrado para os índices fornecidos 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      await collection.updateOne(
        { _id: data.key.remoteJid!, 'groups.name': group_name },
        { $pull: { 'groups.$.participants': { $in: participants_to_remove } } },
      );

      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Participantes removidos do grupo *${group_name}* com sucesso! 🎉` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui remover os participantes 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }

  private async mention(data: CommandData, rest_command: string): Promise<Message[]> {
    try {
      await this.client.connect();
      const database = this.client.db('resenhazord2');
      const collection = database.collection<GroupsDoc>('groups_mentions');

      const response = await collection.findOne({ _id: data.key.remoteJid! });
      const empty_groups = !response || response?.groups?.length == 0;
      if (empty_groups) {
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Você não tem grupos 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }

      const groups = response!.groups;
      const group_name = rest_command.split(/\s+/)[0];
      const text = rest_command.replace(group_name, '').trim();
      const group = groups.find((group) => group.name === group_name);
      if (!group) {
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: `Não existe um grupo com o nome *${rest_command}* 😔` },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }
      const regex = /@lid|@s.whatsapp.net/gi;
      const message = text.length > 0 ? `${text}\n\n` : '';
      const mentions = group.participants.map(
        (participant) => `@${participant.replace(regex, '')}`,
      );
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `${message}${mentions.join(' ')}`, mentions: group.participants },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Não consegui marcar os participantes 😔` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }
}
