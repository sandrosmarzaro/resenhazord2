import Resenhazord2 from '../models/Resenhazord2.js'

export default class AddCommand {

    static identifier = "^\\s*\\,\\s*add\\s*(?:\\d+)?\\s*$";

    static DDD_LIST = [
        '11','12','13','14','15','16','17','18','19','21','22','24','27','28','31',
        '32','33','34','35','37','38','41','42','43','44','45','46','47','48','49',
        '51','53','54','55','61','62','63','64','65','66','67','68','69','71','73',
        '74','75','77','79','81','82','83','84','85','86','87','88','89','91','92',
        '93','94','95','96','97','98','99'
    ];

    static async run(data) {
        console.log('ADD COMMAND');

        const chat = await data.getChat();
        if (!chat.isGroup) {
            chat.sendMessage(
                `Burro burro! Você só pode adicionar alguém em um grupo! 🤦‍♂️`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const { participants } = chat;
        const { RESENHAZORD2_ID } = process.env;
        const is_resenhazord2_admin = participants.find(
            participant => participant.id._serialized === RESENHAZORD2_ID
        ).isAdmin;
        if (!is_resenhazord2_admin) {
            chat.sendMessage(
                `Vai se foder! Eu não sou admin! 🖕`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        const rest_command = data.body.replace(/\n*\s*\,\s*add\s*/, '');
        const inserted_phone = rest_command.replace(/\s|\n/, '');
        if (inserted_phone.length == 0) {
            this.build_and_send_phone(inserted_phone, chat);
            return;
        }

        const is_valid_DDD = this.DDD_LIST.some(DDD => inserted_phone.startsWith(DDD));
        if (!is_valid_DDD) {
            chat.sendMessage(
                `Burro burro! O DDD do estado 🏳️‍🌈 não existe!`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
            return;
        }

        if (inserted_phone.length > 11) {
            chat.sendMessage(
                `Aiiiiii, o tamanho do telefone é desse ✋   🤚 tamanho, só aguento 11cm`,
                { sendSeen: true, quotedMessageId: data.id._serialized }
            );
        }

        this.build_and_send_phone(inserted_phone, chat);
    }

    static async build_and_send_phone(initial_phone, chat) {
        if (initial_phone.length == 0) {
            const random_ddd = this.DDD_LIST[Math.floor(Math.random() * this.DDD_LIST.length)];
            initial_phone += random_ddd;
        }

        if (initial_phone.length == 2) {
            const ddds_starts_eith = ['31', '32', '34', '35', '61', '83']
            if (ddds_starts_eith.some(prefix => initial_phone.startsWith(prefix))) {
                initial_phone += '8';
            }
            else {
                initial_phone += '9';
            }
        }

        let is_sucefull = false;
        let tries = 0;
        const is_complete_phone = initial_phone.length >= 10;
        console.log('initial phone:', initial_phone);
        console.log('is complete phone:', is_complete_phone);
        do {
            console.log('------------------- new loop -------------------');
            console.log(`start phone: ${initial_phone}`);
            let generated_phone = initial_phone;

            if (!is_complete_phone) {
                let size_phone = Math.random() < 0.5 ? 11 : 10;
                console.log('size:', size_phone);

                while (generated_phone.length != size_phone) {
                    generated_phone += Math.floor(Math.random() * 10);
                }
                console.log('generated phone:', generated_phone);
            }
            else {
                is_sucefull = true;
            }

            let has_wa = await Resenhazord2.client.isRegisteredUser(`55${generated_phone}@c.us`);
            console.log('is registered:', has_wa);
            if (has_wa) {
                await chat.addParticipants([`55${generated_phone}@c.us`]);
                is_sucefull = true;
            }
            else {
                generated_phone = '';
            }
            tries++;
        } while (!is_sucefull);
        console.log('------------------- end loop -------------------')
        console.log('tries:', tries);
    }
}