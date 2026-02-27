import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class MateusCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*mateus\\s*$';
  readonly menuDescription = 'Descubra a probabilidade do Mateus nascer.';

  async run(data: CommandData): Promise<void> {
    const probability = (Math.random() * 101).toFixed(2).replace('.', ',');
    try {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `A probabilidade de Mateus nascer agora é de ${probability} % 🧐` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR MATEUS COMMAND\n${error}`);
    }
  }
}
