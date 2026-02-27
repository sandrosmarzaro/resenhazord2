import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { NSFW } from 'nsfwhub';

export default class FuckCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*fuck\\s*(?:\\@\\d+\\s*)$';
  readonly menuDescription = 'Foda a pessoa mencionada mandando uma foto de pornozão pra ela.';

  async run(data: CommandData): Promise<Message[]> {
    const regex = /@lid|@s.whatsapp.net/gi;
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode fuder com alguém do grupo em um! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
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
