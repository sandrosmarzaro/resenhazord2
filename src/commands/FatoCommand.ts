import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class FatoCommand {
  static identifier: string = '^\\s*\\,\\s*fato\\s*(?:hoje)?\\s*$';

  static async run(data: CommandData): Promise<void> {
    const rest_command = data.text.replace(/\n*\s*,\s*fato\s*/, '');
    const rest_link = rest_command.match(/hoje/) ? 'today' : 'random';
    const url = `https://uselessfacts.jsph.pl/api/v2/facts/${rest_link}`;

    const response = await fetch(url);
    const fact = await response.json();
    try {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `FATO 🤓☝️\n${fact.text}` },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR FATO COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Não consegui te dar um fato... 😔' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
