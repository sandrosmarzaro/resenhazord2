import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { SWEARINGS } from '../data/swearings.js';
import Reply from '../builders/Reply.js';

export default class AdmCommand extends Command {
  readonly config: CommandConfig = { name: 'adm', groupOnly: true };
  readonly menuDescription = 'Xingue aleatoriamente todos os administradores do grupo.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const { participants } = await this.whatsapp!.groupMetadata(data.key.remoteJid!);
    const adms = participants.filter((participant) => participant.admin);
    const adms_ids = adms.map((adm) => adm.id);
    const regex = /@lid|@s.whatsapp.net/gi;
    const adm_mentions = adms.map((adm) => `@${adm.id.replace(regex, '')} `);
    const random_swearing = SWEARINGS[Math.floor(Math.random() * SWEARINGS.length)];
    return [
      Reply.to(data).textWith(
        `Vai se foder administração! 🖕\nVocê é ${random_swearing}\n${adm_mentions.join('')}`,
        adms_ids,
      ),
    ];
  }
}
