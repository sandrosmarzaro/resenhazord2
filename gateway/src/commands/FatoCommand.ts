import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';

export default class FatoCommand extends Command {
  readonly config: CommandConfig = { name: 'fato', flags: ['hoje'], category: 'aleatórias' };
  readonly menuDescription = 'Descubra um fato aleatório ou de hoje em inglês.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const rest_link = parsed.flags.has('hoje') ? 'today' : 'random';
    const url = `https://uselessfacts.jsph.pl/api/v2/facts/${rest_link}`;

    const response = await AxiosClient.get<{ text: string }>(url);
    const fact = response.data;
    return [Reply.to(data).text(`FATO 🤓☝️\n${fact.text}`)];
  }
}
