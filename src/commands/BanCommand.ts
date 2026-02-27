import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class BanCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*ban\\s*(?:\\@\\d+\\s*)*\\s*$';
  readonly menuDescription =
    'Remove aleatoriamente um ou especificamente um ou mais participantes do grupo.';

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode remover alguém em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const regex = /@lid|@s.whatsapp.net/gi;
    const group = await Resenhazord2.socket!.groupMetadata(data.key.remoteJid!);
    const { participants } = group;
    const { RESENHAZORD2_JID } = process.env;
    const is_resenhazord2_admin = participants.find(
      (participant) => participant.id === RESENHAZORD2_JID,
    )?.admin;
    if (!is_resenhazord2_admin) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Vai se foder! Eu não sou admin! 🖕` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
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
          await Resenhazord2.socket!.groupParticipantsUpdate(
            data.key.remoteJid!,
            [random_participant.id],
            'remove',
          );
          messages.push({
            jid: data.key.remoteJid!,
            content: {
              text: `Se fudeu! @${random_participant.id.replace(regex, '')} 🖕`,
              mentions: [random_participant.id],
            },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          });
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
        await Resenhazord2.socket!.groupParticipantsUpdate(
          data.key.remoteJid!,
          [participant],
          'remove',
        );
        const participant_phone = participant.replace(regex, '');
        messages.push({
          jid: data.key.remoteJid!,
          content: { text: `Se fudeu! @${participant_phone} 🖕`, mentions: [participant] },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        });
      }
    }
    return messages;
  }
}
