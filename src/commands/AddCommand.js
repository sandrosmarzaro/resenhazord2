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

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode adicionar alguém em um grupo! 🤦‍♂️`},
                {quoted: data}
            );
            return;
        }

        const { participants } = await Resenhazord2.socket.groupMetadata(data.key.remoteJid);
        const { RESENHAZORD2_ID } = process.env;
        const is_resenhazord2_admin = participants.find(
            participant => participant.id === RESENHAZORD2_ID
        ).admin;
        if (!is_resenhazord2_admin) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Vai se fuder! Eu não sou admin! 🖕`},
                {quoted: data}
            );
            return;
        }

        const rest_command = data.message.extendedTextMessage.text.replace(/\n*\s*\,\s*add\s*/, '');
        const inserted_phone = rest_command.replace(/\s|\n/, '');
        if (inserted_phone.length == 0) {
            this.build_and_send_phone(inserted_phone, data);
            return;
        }

        const is_valid_DDD = this.DDD_LIST.some(DDD => inserted_phone.startsWith(DDD));
        if (!is_valid_DDD) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! O DDD do estado 🏳️‍🌈 não existe!`},
                {quoted: data}
            );
            return;
        }

        if (inserted_phone.length > 11) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Aiiiiii, o tamanho do telefone é desse ✋   🤚 tamanho, só aguento 11cm`},
                {quoted: data}
            );
        }

        this.build_and_send_phone(inserted_phone, data);
    }

    static async build_and_send_phone(initial_phone, data) {
        let is_sucefull = false;
        let tries = 0;
        const is_complete_phone = initial_phone.length >= 10;
        console.log('is complete phone:', is_complete_phone);
        do {
            console.log('------------------- new loop -------------------');
            let generated_phone = '';
            if (initial_phone.length === 0) {
                let random_ddd = this.DDD_LIST[Math.floor(Math.random() * this.DDD_LIST.length)];
                generated_phone += initial_phone + random_ddd;
            }

            if (generated_phone.length == 2) {
                const ddds_starts_eith = ['31', '32', '34', '35', '61', '83']
                if (ddds_starts_eith.some(prefix => initial_phone.startsWith(prefix))) {

                    generated_phone += initial_phone + '8';
                }
                else {
                    generated_phone += initial_phone + '9';
                }
            }

            console.log(`start phone: ${generated_phone}`);
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

            const consult = await Resenhazord2.socket.onWhatsApp(`55${generated_phone}`);
            console.log('consult:', consult);
            if (consult[0]?.exists || is_complete_phone) {
                try {
                    const id = consult[0]?.exists ? consult[0]?.jid : '55' + initial_phone + '@s.whatsapp.net';
                    await Resenhazord2.socket.groupParticipantsUpdate(
                        data.key.remoteJid,
                        [id],
                        "add"
                    );
                }
                catch (error) {
                    console.error('ERROR ADD COMMAND', error);
                    Resenhazord2.socket.sendMessage(
                        data.key.remoteJid,
                        {text: `Não consegui adicionar o número ${generated_phone} 😔`},
                        {quoted: data}
                    );
                }
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