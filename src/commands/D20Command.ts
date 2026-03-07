import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';

export default class D20Command extends Command {
  readonly config: CommandConfig = { name: 'd20', category: 'aleatórias' };
  readonly menuDescription = 'Role um dado de vinte dimensões.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const d20 = Math.floor(Math.random() * 20) + 1;
    return [Reply.to(data).text(`Aqui está sua rolada: ${d20} 🎲`)];
  }
}
