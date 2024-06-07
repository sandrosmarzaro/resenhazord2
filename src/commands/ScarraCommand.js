import Resenhazord2 from "../models/Resenhazord2.js";

export default class ScarraCommand {

    static identifier = "^\\s*\\,\\s*scarra\\s*$";

    static async run(data) {
        console.log('SCARRA COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        if (!data.key.remoteJid.match(/g.us/)) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Burro burro! Você só pode escarrar alguém em um grupo! 🤦‍♂️`},
                {quoted: data, ephemeralExpiration: exp}
            );
            return;
        }

        const message = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
        if (!message?.viewOnceMessage && !message?.viewOnceMessageV2 && !message?.viewOnceMessageV2Extension) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Burro burro! Você precisa marcar uma mensagem única pra eu escarrar! 🤦‍♂️'},
                {quoted: data, ephemeralExpiration: exp}
            );
            return;
        }

        const json_message = JSON.stringify(message);
        let parsed_message = JSON.parse(json_message);
        const caption = `Escarrado! 😝`;
        const viewOnceTypes = ['imageMessage', 'videoMessage', 'audioMessage'];

        for (const type of viewOnceTypes) {
            if (parsed_message.viewOnceMessageV2?.message?.[type]) {
                parsed_message.viewOnceMessageV2.message[type].viewOnce = false;
                if (!parsed_message.viewOnceMessageV2.message[type].caption) {
                    parsed_message.viewOnceMessageV2.message[type].caption = caption;
                }
                if (!parsed_message.viewOnceMessageV2.message[type].contextInfo) {
                    parsed_message.viewOnceMessageV2.message[type].contextInfo = {};
                }
                break;
            } else if (parsed_message.viewOnceMessageV2Extension?.message?.[type]) {
                parsed_message.viewOnceMessageV2Extension.message[type].viewOnce = false;
                if (!parsed_message.viewOnceMessageV2Extension.message[type].caption) {
                    parsed_message.viewOnceMessageV2Extension.message[type].caption = caption;
                }
                if (!parsed_message.viewOnceMessageV2Extension.message[type].contextInfo) {
                    parsed_message.viewOnceMessageV2Extension.message[type].contextInfo = {};
                }
                break;
            } else if (parsed_message.viewOnceMessage?.message?.[type]) {
                parsed_message.viewOnceMessage.message[type].viewOnce = false;
                if (!parsed_message.viewOnceMessage.message[type].caption) {
                    parsed_message.viewOnceMessage.message[type].caption = caption;
                }
                if (!parsed_message.viewOnceMessage.message[type].contextInfo) {
                    parsed_message.viewOnceMessage.message[type].contextInfo = {};
                }
                break;
            }
        }
        Resenhazord2.socket.relayMessage(data.key.remoteJid, parsed_message, { }).catch(error => {
            console.error('ERROR SCARRA COMMAND', error)
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui escarrar! 😔`},
                {quoted: data, ephemeralExpiration: exp}
            );
        });
    }
}