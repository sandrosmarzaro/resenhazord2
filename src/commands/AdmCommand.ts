import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { SWEARINGS } from '../data/swearings.js';

export default class AdmCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*adm\\s*$';
  readonly menuDescription = 'Xingue aleatoriamente todos os administradores do grupo.';

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode xingar adminstração em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const { participants } = await Resenhazord2.socket!.groupMetadata(data.key.remoteJid!);
    const adms = participants.filter((participant) => participant.admin);
    const adms_ids = adms.map((adm) => adm.id);
    const regex = /@lid|@s.whatsapp.net/gi;
    const adm_mentions = adms.map((adm) => `@${adm.id.replace(regex, '')} `);
    const random_swearing = SWEARINGS[Math.floor(Math.random() * SWEARINGS.length)];
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          text: `Vai se foder administração! 🖕\nVocê é ${random_swearing}\n${adm_mentions.join('')}`,
          mentions: adms_ids,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
