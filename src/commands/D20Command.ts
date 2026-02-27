import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class D20Command extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*d20\\s*$';
  readonly menuDescription = 'Role um dado de vinte dimensões.';

  async run(data: CommandData): Promise<Message[]> {
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
