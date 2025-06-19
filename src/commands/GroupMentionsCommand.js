import Resenhazord2 from "../models/Resenhazord2.js";
import { MongoClient } from 'mongodb';

export default class GroupMentionsCommand {

    static identifier = "^\\s*\\,\\s*grupo\\s*";
    static client = new MongoClient(process.env.MONGODB_URI);

    static async run(data) {

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode marcar alguém em um grupo! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
        const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
        const rest_command = data.text.replace(/\s*,\s*grupo\s*/, '');

        const has_function = functions.some(func => new RegExp(func, 'i').test(rest_command));
        if (!has_function) {
            this.mention(data, rest_command);
            return;
        }

        for (const func of functions) {
            if (new RegExp(func, 'i').test(rest_command)) {
                this[func](data, rest_command.replace(func, '').replace(/\n/g, '').trim());
            }
        }
    }

    static async create(data, rest_command) {

        const sender_id = data.key.participant;

        const group_name = rest_command.replace(/\s*\@\d+\s*/g, '')
        if (group_name?.length == 0) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Cadê o nome do grupo? 🤔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
        if (group_name?.length > 15) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `O nome do grupo é desse tamanho! ✋    🤚`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
        const functions = ['add', 'exit', 'create', 'delete', 'rename', 'list'];
        if (functions.some(func => new RegExp(func, 'i').test(group_name))) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `O nome do grupo não pode ser um comando!`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const has_group = await collection.findOne({_id: data.key.remoteJid, 'groups.name': group_name});
            if (has_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Já existe um grupo com o nome *${group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const mentioneds = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
            const has_groups = await collection.findOne({_id: data.key.remoteJid});
            if (!has_groups) {
                await collection.insertOne({
                    _id: data.key.remoteJid,
                    groups: [{ name: group_name, participants: [sender_id, ...mentioneds]}]
                });
            }
            else {
                await collection.updateOne(
                    { _id: data.key.remoteJid },
                    { $push: { groups: { name: group_name, participants: [sender_id, ...mentioneds] } } }
                );
            }
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Grupo *${group_name}* criado com sucesso! 🎉`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui criar o grupo *${group_name}* 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async rename(data, rest_command) {

        const has_two_groups = rest_command.match(/[\S]+\s+[\S]+/);
        if (!has_two_groups) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Cadê os nomes dos grupos? 🤔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const [old_group_name, new_group_name] = rest_command.split(/\s+/);
        try {

            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const has_old_group = await collection.findOne({
                _id: data.key.remoteJid,
                'groups.name': old_group_name
            });
            if (!has_old_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Não existe um grupo com o nome *${old_group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const has_new_group = await collection.findOne({
                _id: data.key.remoteJid,
                'groups.name': new_group_name
            });
            if (has_new_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Já existe um grupo com o nome *${new_group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            await collection.updateOne(
                { _id: data.key.remoteJid, 'groups.name': old_group_name },
                { $set: { 'groups.$.name': new_group_name } }
            );
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Grupo *${old_group_name}* renomeado para *${new_group_name}* com sucesso! 🎉`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );

        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui renomear o grupo *${old_group_name}* 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async delete(data, rest_command) {

        const group_name = rest_command;
        if (group_name?.length == 0) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Cadê o nome do grupo? 🤔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const has_group = await collection.findOne({_id: data.key.remoteJid, 'groups.name': group_name});
            if (!has_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Não existe um grupo com o nome *${group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            await collection.updateOne(
                { _id: data.key.remoteJid },
                { $pull: { groups: { name: group_name } } }
            );
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Grupo *${group_name}* deletado com sucesso! 🎉`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui deletar o grupo *${group_name}* 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async list(data, rest_command) {

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const response = await collection.findOne({_id: data.key.remoteJid});
            const empty_groups = !response || response?.groups?.length == 0;
            if (empty_groups) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Você não tem grupos 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            if (rest_command?.length > 0) {
                const group = response.groups.find(group => group.name === rest_command);
                if (!group) {
                    Resenhazord2.socket.sendMessage(
                        data.key.remoteJid,
                        {text: `Não existe um grupo com o nome *${rest_command}* 😔`},
                        {quoted: data, ephemeralExpiration: data.expiration}
                    );
                    return;
                }
                const message = group.participants.map(
                    participant => `- ${participant.replace('@s.whatsapp.net', '')}`)
                    .join('\n');
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `📜 *${rest_command.toUpperCase()}* 📜\n\n${message}`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const message = response.groups.map(group => `- _${group.name}_`).join('\n');
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `📜 *GRUPOS* 📜\n\n${message}`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui listar os grupos 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async add(data, rest_command) {

        const sender_id = data.key.participant;

        const group_name = rest_command.replace(/\s*\@\d+\s*/g, '');
        if (group_name?.length == 0) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Cadê o nome do grupo? 🤔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const has_group = await collection.findOne({_id: data.key.remoteJid, 'groups.name': group_name});
            if (!has_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Não existe um grupo com o nome *${group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const participants = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
            if (participants.length == 0) {
                await collection
                    .updateOne(
                        { _id: data.key.remoteJid, 'groups.name': group_name },
                        { $addToSet: { 'groups.$.participants': sender_id } }
                    );
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Você foi adicionado ao grupo *${group_name}* com sucesso! 🎉`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
            else {
                await collection
                    .updateOne(
                        { _id: data.key.remoteJid, 'groups.name': group_name },
                        { $addToSet: { 'groups.$.participants': { $each: participants } } }
                    );
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Participantes adicionados ao grupo *${group_name}* com sucesso! 🎉`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui adicionar os participantes 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async exit(data, rest_command) {

        const sender_id = data.key.participant;
        const has_mention = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid?.length > 0;
        if (has_mention) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você não marcou ninguém! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const group_name = rest_command.replace(/\s*\@\d+\s*/g, '');
        if (group_name?.length == 0) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Cadê o nome do grupo? 🤔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const has_group = await collection.findOne({_id: data.key.remoteJid, 'groups.name': group_name});
            if (!has_group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Não existe um grupo com o nome *${group_name}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const mentioneds = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
            if (mentioneds.length == 0) {
                await collection
                    .updateOne(
                        { _id: data.key.remoteJid, 'groups.name': group_name },
                        { $pull: { 'groups.$.participants': sender_id } }
                    );
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Você foi removido do grupo *${group_name}* com sucesso! 🎉`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
            else {
                await collection
                    .updateOne(
                        { _id: data.key.remoteJid, 'groups.name': group_name },
                        { $pull: { 'groups.$.participants': { $in: mentioneds } } }
                    );
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Participantes removidos do grupo *${group_name}* com sucesso! 🎉`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
            }
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui remover os participantes 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }

    static async mention(data, rest_command) {

        try {
            await this.client.connect();
            const database = this.client.db('resenhazord2');
            const collection = database.collection('groups_mentions');

            const response = await collection.findOne({_id: data.key.remoteJid});
            const empty_groups = !response || response?.groups?.length == 0;
            if (empty_groups) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Você não tem grupos 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }

            const group_name = rest_command.split(/\s+/)[0];
            const text = rest_command.replace(group_name, '').trim();
            const group = response.groups.find(group => group.name === group_name);
            if (!group) {
                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {text: `Não existe um grupo com o nome *${rest_command}* 😔`},
                    {quoted: data, ephemeralExpiration: data.expiration}
                );
                return;
            }
            const message = text.length > 0 ? `${text}\n\n` : '';
            const mentions = group.participants.map(
                participant => `@${participant.replace('@s.whatsapp.net', '')}`
            );
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `${message}${mentions.join(' ')}`, mentions: group.participants},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR GROUP MENTIONS COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui marcar os participantes 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }
    }
}