import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { DDD_LIST } from '../data/dddList.js';

export default class AddCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$';
  readonly menuDescription = 'Adiciona um número ao grupo. Aleatório ou específico.';

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

    const is_valid_DDD = DDD_LIST.some((DDD) => inserted_phone.startsWith(DDD));
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
        const random_ddd = DDD_LIST[Math.floor(Math.random() * DDD_LIST.length)];
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
