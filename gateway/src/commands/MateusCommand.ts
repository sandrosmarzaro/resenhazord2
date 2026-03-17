import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import Reply from '../builders/Reply.js';

export default class MateusCommand extends Command {
  readonly config: CommandConfig = { name: 'mateus', category: 'aleatórias' };
  readonly menuDescription = 'Descubra a probabilidade do Mateus nascer.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const probability = (Math.random() * 101).toFixed(2).replace('.', ',');
    return [Reply.to(data).text(`A probabilidade de Mateus nascer agora é de ${probability} % 🧐`)];
  }
}
