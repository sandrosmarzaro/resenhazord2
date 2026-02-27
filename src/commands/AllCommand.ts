import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class AllCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*all\\s*';
  readonly menuDescription = 'Marca todos os participantes do grupo com ou sem uma mensagem.';

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode marcar o grupo em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const { participants } = await Resenhazord2.socket!.groupMetadata(data.key.remoteJid!);
    const text_inserted = data.text.replace(/\n*\s*,\s*all\s*/, '');
    let message = text_inserted.length > 0 ? text_inserted : '';
    message += '\n\n';
    const regex = /@lid|@s.whatsapp.net/gi;
    for (const participant of participants) {
      message += `@${participant.id.replace(regex, '')} `;
    }
    const participants_ids = participants.map((participant) => participant.id);
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: message, mentions: participants_ids },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
