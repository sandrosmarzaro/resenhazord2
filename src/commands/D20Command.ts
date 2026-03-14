import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import Reply from '../builders/Reply.js';

export default class D20Command extends Command {
  readonly config: CommandConfig = { name: 'd20', category: 'aleatórias' };
  readonly menuDescription = 'Role um dado de vinte dimensões.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const d20 = Math.floor(Math.random() * 20) + 1;
    return [Reply.to(data).text(`Aqui está sua rolada: ${d20} 🎲`)];
  }
}
