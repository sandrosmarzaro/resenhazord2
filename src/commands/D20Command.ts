import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class D20Command extends Command {
  readonly config: CommandConfig = { name: 'd20' };
  readonly menuDescription = 'Role um dado de vinte dimensões.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const d20 = Math.floor(Math.random() * 20) + 1;
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `Aqui está sua rolada: ${d20} 🎲` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
