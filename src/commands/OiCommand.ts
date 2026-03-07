import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';

export default class OiCommand extends Command {
  readonly config: CommandConfig = { name: 'oi', category: 'outras' };
  readonly menuDescription = 'Apenas diga oi ao bot.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const sender = (data.key.participant ?? data.key.remoteJid)!;
    const sender_phone = sender.replace(/@lid/, '');
    return [Reply.to(data).textWith(`Vai se fuder @${sender_phone} filho da puta! 🖕`, [sender])];
  }
}
