import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';

export default class AddCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$';
  readonly menuDescription = 'Adiciona um número ao grupo. Aleatório ou específico.';

  private readonly DDD_LIST = [
    '11',
    '12',
    '13',
    '14',
    '15',
    '16',
    '17',
    '18',
    '19',
    '21',
    '22',
    '24',
    '27',
    '28',
    '31',
    '32',
    '33',
    '34',
    '35',
    '37',
    '38',
    '41',
    '42',
    '43',
    '44',
    '45',
    '46',
    '47',
    '48',
    '49',
    '51',
    '53',
    '54',
    '55',
    '61',
    '62',
    '63',
    '64',
    '65',
    '66',
    '67',
    '68',
    '69',
    '71',
    '73',
    '74',
    '75',
    '77',
    '79',
    '81',
    '82',
    '83',
    '84',
    '85',
    '86',
    '87',
    '88',
    '89',
    '91',
    '92',
    '93',
    '94',
    '95',
    '96',
    '97',
    '98',
    '99',
  ];

  async run(data: CommandData): Promise<Message[]> {
    if (!data.key.remoteJid!.match(/g.us/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! Você só pode adicionar alguém em um grupo! 🤦‍♂️` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const { participants } = await Resenhazord2.socket!.groupMetadata(data.key.remoteJid!);
    const { RESENHAZORD2_JID } = process.env;
    const is_resenhazord2_admin = participants.find(
      (participant) => participant.id === RESENHAZORD2_JID,
    )!.admin;
    if (!is_resenhazord2_admin) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Vai se fuder! Eu não sou admin! 🖕` },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const rest_command = data.text.replace(/\n*\s*,\s*add\s*/, '');
    const inserted_phone = rest_command.replace(/\s|\n/, '');
    if (inserted_phone.length == 0) {
      return await this.build_and_send_phone(inserted_phone, data);
    }

    const is_valid_DDD = this.DDD_LIST.some((DDD) => inserted_phone.startsWith(DDD));
    if (!is_valid_DDD) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: `Burro burro! O DDD do estado 🏳️‍🌈 não existe!` },
          options: { quoted: data },
        },
      ];
    }

    const messages: Message[] = [];
    if (inserted_phone.length > 11) {
      messages.push({
        jid: data.key.remoteJid!,
        content: {
          text: `Aiiiiii, o tamanho do telefone é desse ✋   🤚 tamanho, só aguento 11cm`,
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      });
    }

    const buildMessages = await this.build_and_send_phone(inserted_phone, data);
    messages.push(...buildMessages);
    return messages;
  }

  private async build_and_send_phone(initial_phone: string, data: CommandData): Promise<Message[]> {
    let is_sucefull = false;
    const is_complete_phone = initial_phone.length >= 10;
    do {
      let generated_phone = '';
      if (initial_phone.length === 0) {
        const random_ddd = this.DDD_LIST[Math.floor(Math.random() * this.DDD_LIST.length)];
        generated_phone += initial_phone + random_ddd;
      }

      if (generated_phone.length == 2) {
        const ddds_starts_eith = ['31', '32', '34', '35', '61', '83'];
        if (ddds_starts_eith.some((prefix) => initial_phone.startsWith(prefix))) {
          generated_phone += initial_phone + '8';
        } else {
          generated_phone += initial_phone + '9';
        }
      }

      if (!is_complete_phone) {
        const size_phone = Math.random() < 0.5 ? 11 : 10;

        while (generated_phone.length != size_phone) {
          generated_phone += Math.floor(Math.random() * 10);
        }
      } else {
        is_sucefull = true;
      }

      const consult = await Resenhazord2.socket!.onWhatsApp(`55${generated_phone}`);
      if (consult?.[0]?.exists || is_complete_phone) {
        try {
          const id = consult?.[0]?.exists ? consult[0]?.jid : '55' + initial_phone + '@lid';
          await Resenhazord2.socket!.groupParticipantsUpdate(data.key.remoteJid!, [id!], 'add');
        } catch (error) {
          console.log(`ERROR ADD COMMAND\n${error}`);
          return [
            {
              jid: data.key.remoteJid!,
              content: { text: `Não consegui adicionar o número ${generated_phone} 😔` },
              options: { quoted: data, ephemeralExpiration: data.expiration },
            },
          ];
        }
        is_sucefull = true;
      }
    } while (!is_sucefull);
    return [];
  }
}
