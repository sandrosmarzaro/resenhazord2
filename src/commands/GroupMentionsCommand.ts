import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
  ArgType,
} from './Command.js';
import Reply from '../builders/Reply.js';
import GroupMentionsService from '../services/GroupMentionsService.js';

type SubHandler = (data: CommandData, rest: string) => Promise<Message[]>;

const RESERVED_KEYWORDS = ['add', 'exit', 'create', 'delete', 'rename', 'list'];

export default class GroupMentionsCommand extends Command {
  readonly config: CommandConfig = {
    name: 'grupo',
    args: ArgType.Optional,
    groupOnly: true,
    category: 'grupo',
  };
  readonly menuDescription = 'Comando complexo. Use *,menu grupo* para detalhes.';

  private readonly service: GroupMentionsService;
  private readonly handlers: Map<string, SubHandler>;

  constructor(service: GroupMentionsService = new GroupMentionsService()) {
    super();
    this.service = service;
    this.handlers = new Map<string, SubHandler>([
      ['create', (data, rest) => this.handleCreate(data, rest)],
      ['rename', (data, rest) => this.handleRename(data, rest)],
      ['delete', (data, rest) => this.handleDelete(data, rest)],
      ['list', (data, rest) => this.handleList(data, rest)],
      ['add', (data, rest) => this.handleAdd(data, rest)],
      ['exit', (data, rest) => this.handleExit(data, rest)],
    ]);
  }

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const rest = parsed.rest;
    for (const [keyword, handler] of this.handlers) {
      if (new RegExp(keyword, 'i').test(rest)) {
        const subRest = rest.replace(new RegExp(keyword, 'i'), '').replace(/\n/g, '').trim();
        return await handler(data, subRest);
      }
    }
    return await this.handleMention(data, rest);
  }

  private validateGroupName(data: CommandData, groupName: string): Message | null {
    if (groupName?.length > 15) {
      return Reply.to(data).text(`O nome do grupo é desse tamanho! ✋    🤚`);
    }
    if (RESERVED_KEYWORDS.some((kw) => new RegExp(kw, 'i').test(groupName))) {
      return Reply.to(data).text(`O nome do grupo não pode ser um comando!`);
    }
    if (groupName.match(/\s/)) {
      return Reply.to(data).text(`O nome do grupo não pode ter espaço!`);
    }
    return null;
  }

  private async handleCreate(data: CommandData, rest: string): Promise<Message[]> {
    const senderJid = (data.key.participant ?? data.key.remoteJid) as string;
    const groupName = rest.replace(/\s*@\d+\s*/g, '');
    if (groupName.length === 0) {
      return [Reply.to(data).text(`Cadê o nome do grupo? 🤔`)];
    }
    const validationError = this.validateGroupName(data, groupName);
    if (validationError) return [validationError];

    const mentioned = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid ?? [];
    const result = await this.service.create(data.key.remoteJid!, senderJid, groupName, mentioned);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    return [Reply.to(data).text(`Grupo *${result.data.groupName}* criado com sucesso! 🎉`)];
  }

  private async handleRename(data: CommandData, rest: string): Promise<Message[]> {
    if (!rest.match(/[\S]+\s+[\S]+/)) {
      return [Reply.to(data).text(`Cadê os nomes dos grupos? 🤔`)];
    }
    const [oldName, newName] = rest.split(/\s+/);
    const validationError = this.validateGroupName(data, newName);
    if (validationError) return [validationError];

    const result = await this.service.rename(data.key.remoteJid!, oldName, newName);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    return [
      Reply.to(data).text(
        `Grupo *${result.data.oldName}* renomeado para *${result.data.newName}* com sucesso! 🎉`,
      ),
    ];
  }

  private async handleDelete(data: CommandData, rest: string): Promise<Message[]> {
    if (rest.length === 0) {
      return [Reply.to(data).text(`Cadê o nome do grupo? 🤔`)];
    }
    const result = await this.service.delete(data.key.remoteJid!, rest);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    return [Reply.to(data).text(`Grupo *${result.data.groupName}* deletado com sucesso! 🎉`)];
  }

  private async handleList(data: CommandData, rest: string): Promise<Message[]> {
    if (rest.length === 0) {
      const result = await this.service.listAll(data.key.remoteJid!);
      if (!result.ok) return [Reply.to(data).text(result.message)];
      const message = result.data.groups.map((g) => `- _${g.name}_`).join('\n');
      return [Reply.to(data).text(`📜 *GRUPOS* 📜\n\n${message}`)];
    }

    const result = await this.service.listOne(data.key.remoteJid!, rest);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    const regex = /@lid|@s.whatsapp.net/gi;
    let message = '';
    for (const [index, id] of result.data.participants.entries()) {
      message += `- ${index + 1}: @${id.replace(regex, '')}\n`;
    }
    return [
      Reply.to(data).textWith(
        `📜 *${rest.toUpperCase()}* 📜\n\n${message}`,
        result.data.participants,
      ),
    ];
  }

  private async handleAdd(data: CommandData, rest: string): Promise<Message[]> {
    const senderJid = (data.key.participant ?? data.key.remoteJid) as string;
    const groupName = rest.replace(/\s*@\d+\s*/g, '');
    if (groupName.length === 0) {
      return [Reply.to(data).text(`Cadê o nome do grupo? 🤔`)];
    }
    const participants = data?.message?.extendedTextMessage?.contextInfo?.mentionedJid ?? [];
    const result = await this.service.add(data.key.remoteJid!, groupName, senderJid, participants);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    const text = result.data.selfOnly
      ? `Você foi adicionado ao grupo *${result.data.groupName}* com sucesso! 🎉`
      : `Participantes adicionados ao grupo *${result.data.groupName}* com sucesso! 🎉`;
    return [Reply.to(data).text(text)];
  }

  private async handleExit(data: CommandData, rest: string): Promise<Message[]> {
    const senderJid = (data.key.participant ?? data.key.remoteJid) as string;
    const groupName = rest.replace(/\s+\d+\s*/g, '');
    if (groupName.length === 0) {
      return [Reply.to(data).text(`Cadê o nome do grupo? 🤔`)];
    }
    const indices = (rest.match(/\s+(\d+)\s*/g) ?? []).map((i) => parseInt(i.trim()));
    const result = await this.service.exit(data.key.remoteJid!, groupName, senderJid, indices);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    const text = result.data.selfOnly
      ? `Você foi removido do grupo *${result.data.groupName}* com sucesso! 🎉`
      : `Participantes removidos do grupo *${result.data.groupName}* com sucesso! 🎉`;
    return [Reply.to(data).text(text)];
  }

  private async handleMention(data: CommandData, rest: string): Promise<Message[]> {
    const groupName = rest.split(/\s+/)[0];
    const text = rest.replace(groupName, '').trim();
    const result = await this.service.mention(data.key.remoteJid!, groupName);
    if (!result.ok) return [Reply.to(data).text(result.message)];
    const regex = /@lid|@s.whatsapp.net/gi;
    const prefix = text.length > 0 ? `${text}\n\n` : '';
    const mentions = result.data.participants.map((p) => `@${p.replace(regex, '')}`);
    return [Reply.to(data).textWith(`${prefix}${mentions.join(' ')}`, result.data.participants)];
  }
}
