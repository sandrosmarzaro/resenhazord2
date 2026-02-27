import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';

export default class OiCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*oi\\s*$';
  readonly menuDescription = 'Apenas diga oi ao bot.';

  async run(data: CommandData): Promise<Message[]> {
    const sender = (data.key.participant ?? data.key.remoteJid)!;
    const sender_phone = sender.replace(/@lid/, '');
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
          mentions: [sender],
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
