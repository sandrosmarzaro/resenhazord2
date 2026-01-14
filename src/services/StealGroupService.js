import Resenhazord2 from '../models/Resenhazord2.js';
import { MongoClient } from 'mongodb';
import axios from 'axios';


export default class StealGroupService {

    static async run(data) {
        if (data.action != 'promote') {
            return;
        }
        let has_promoted = false;
        const { RESENHAZORD2_JID, RESENHA_JID } = process.env;
        for (const participant of data.participants) {
            if (participant.phoneNumber == RESENHAZORD2_JID) {
                has_promoted = true;
                break;
            }
        }
        if (!has_promoted) {
            return;
        }
        const uri = process.env.MONGODB_URI;
        const client = new MongoClient(uri);
        try {
            const { participants, ownerPn, subject, desc } = await Resenhazord2.socket.groupMetadata(data.id);
            const admin_participants = participants
                .filter(participant => participant.admin && participant.phoneNumber != RESENHAZORD2_JID)
                .map(participant => participant.phoneNumber);
            const has_admin_owner = admin_participants.includes(ownerPn);
            if (has_admin_owner) {
                return;
            }
            await Resenhazord2.socket.groupParticipantsUpdate(
                data.id,
                admin_participants,
                'demote'
            );
            await client.connect();
            const database = client.db('resenhazord2');
            const collection = database.collection('colonias');
            const result = await collection.findOneAndUpdate(
                { _id: 'counter' },
                { $inc: { number: 1 } },
                { returnDocument: 'after', upsert: true }
            );
            let colony_number = result.number
            const roman_numerals = {
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
                1: 'I'
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
            await Resenhazord2.socket.groupUpdateSubject(
                data.id,
                `Colônia da Resenha ${roman_number} 🐮🎣🍆`
            );
            await Resenhazord2.socket.sendMessage(
                RESENHA_JID,
                {text: 'Colônia obtida!\n\n'+ `*${subject}\n*` + desc},
                {ephemeralExpiration: 86400}
            );
            await Resenhazord2.socket.groupUpdateDescription(
                data.id,
                'Este grupo pertece agora a Resenha 🔒'
            );
            const image_response = await axios.get('https://loremflickr.com/900/900/', {
                responseType: 'arraybuffer'
            });
            const image_buffer = Buffer.from(image_response.data, 'binary');
            await Resenhazord2.socket.updateProfilePicture(
                data.id,
                image_buffer
            );
        }
        catch {
            return;
        }
        finally {
            await client.close();
        }
    }
}