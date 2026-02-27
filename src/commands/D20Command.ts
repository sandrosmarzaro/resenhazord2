import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class D20Command extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*d20\\s*$';
  readonly menuDescription = 'Role um dado de vinte dimensões.';

  async run(data: CommandData): Promise<void> {
    const d20 = Math.floor(Math.random() * 20) + 1;
    try {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Aqui está sua rolada: ${d20} 🎲` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR D20 COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Não consegui te dar uma rolada... 😔' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
