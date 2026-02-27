import type { CommandData } from '../types/command.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class OiCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*oi\\s*$';
  readonly menuDescription = 'Apenas diga oi ao bot.';

  async run(data: CommandData): Promise<void> {
    const sender = (data.key.participant ?? data.key.remoteJid)!;
    const sender_phone = sender.replace(/@lid/, '');
    try {
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        {
          text: `Vai se fuder @${sender_phone} filho da puta! 🖕`,
          mentions: [sender],
        },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR OI COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: `Não consegui responder @${sender_phone} 😔`, mentions: [sender] },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    }
  }
}
