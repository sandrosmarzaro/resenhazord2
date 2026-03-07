import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import { NSFW } from 'nsfwhub';
import Reply from '../builders/Reply.js';

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
      Reply.to(data).raw({
        viewOnce: true,
        video: { url: porn.image.url },
        mentions: [sender, data.message!.extendedTextMessage!.contextInfo!.mentionedJid![0]],
        caption: `@${sender_phone} está fudendo @${mentioned_phone} 😩`,
      }),
    ];
  }
}
