import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class MateusCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*mateus\\s*$';
  readonly menuDescription = 'Descubra a probabilidade do Mateus nascer.';

  async run(data: CommandData): Promise<Message[]> {
    const probability = (Math.random() * 101).toFixed(2).replace('.', ',');
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `A probabilidade de Mateus nascer agora é de ${probability} % 🧐` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
