import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';

export default class BanCommand extends Command {
  readonly config: CommandConfig = {
    name: 'ban',
    args: ArgType.Optional,
    argsPattern: /^(?:@\d+(?:\s+@\d+)*)?$/,
    argsLabel: '@número',
    groupOnly: true,
    category: 'grupo',
  };
  readonly menuDescription =
    'Remove aleatoriamente um ou especificamente um ou mais participantes do grupo.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const regex = /@lid|@s.whatsapp.net/gi;
    const group = await this.whatsapp!.groupMetadata(data.key.remoteJid!);
    const { participants } = group;
    const { RESENHAZORD2_JID } = process.env;
    const is_resenhazord2_admin = participants.find(
      (participant) => participant.id === RESENHAZORD2_JID,
    )?.admin;
    if (!is_resenhazord2_admin) {
      return [Reply.to(data).text(`Vai se foder! Eu não sou admin! 🖕`)];
    }

    const messages: Message[] = [];
    const ban_list = data.message?.extendedTextMessage?.contextInfo?.mentionedJid;
    if (!ban_list?.length) {
      let is_bot;
      do {
        const random_participant = participants[Math.floor(Math.random() * participants.length)];
        is_bot =
          random_participant.id === RESENHAZORD2_JID || random_participant.id === group.owner;
        if (!is_bot) {
          await this.whatsapp!.groupParticipantsUpdate(
            data.key.remoteJid!,
            [random_participant.id],
            'remove',
          );
          messages.push(
            Reply.to(data).textWith(`Se fudeu! @${random_participant.id.replace(regex, '')} 🖕`, [
              random_participant.id,
            ]),
          );
        }
      } while (!is_bot);
    } else {
      const owner_is_admin = participants.find(
        (participant) => participant.id === group.owner,
      )?.admin;
      for (const participant of ban_list) {
        if (participant === RESENHAZORD2_JID || (participant === group.owner && owner_is_admin)) {
          continue;
        }
        await this.whatsapp!.groupParticipantsUpdate(data.key.remoteJid!, [participant], 'remove');
        const participant_phone = participant.replace(regex, '');
        messages.push(Reply.to(data).textWith(`Se fudeu! @${participant_phone} 🖕`, [participant]));
      }
    }
    return messages;
  }
}
