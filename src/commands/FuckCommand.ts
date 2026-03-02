import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import { NSFW } from 'nsfwhub';

export default class FuckCommand extends Command {
  readonly config: CommandConfig = {
    name: 'fuck',
    args: ArgType.Required,
    argsPattern: /^@\d+\s*$/,
    groupOnly: true,
  };
  readonly menuDescription = 'Foda a pessoa mencionada mandando uma foto de pornozão pra ela.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const regex = /@lid|@s.whatsapp.net/gi;
    const sender = (data.key.participant ?? data.key.remoteJid)!;
    const sender_phone = sender.replace(/@lid/, '');
    const mentioned_phone =
      data.message!.extendedTextMessage!.contextInfo!.mentionedJid![0].replace(regex, '');

    const nsfw = new NSFW();
    const porn = await nsfw.fetch('fuck');
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          viewOnce: true,
          video: { url: porn.image.url },
          mentions: [sender, data.message!.extendedTextMessage!.contextInfo!.mentionedJid![0]],
          caption: `@${sender_phone} está fudendo @${mentioned_phone} 😩`,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
