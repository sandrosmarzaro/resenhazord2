import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class FatoCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*fato\\s*(?:hoje)?\\s*$';
  readonly menuDescription = 'Descubra um fato aleatório ou de hoje em inglês.';

  async run(data: CommandData): Promise<Message[]> {
    const rest_command = data.text.replace(/\n*\s*,\s*fato\s*/, '');
    const rest_link = rest_command.match(/hoje/) ? 'today' : 'random';
    const url = `https://uselessfacts.jsph.pl/api/v2/facts/${rest_link}`;

    const response = await fetch(url);
    const fact = await response.json();
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `FATO 🤓☝️\n${fact.text}` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
