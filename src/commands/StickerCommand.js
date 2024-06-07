import Resenhazord2 from "../models/Resenhazord2.js";
import { downloadMediaMessage } from "@whiskeysockets/baileys";
import sharp from "sharp";

export default class StickerCommand {

    static identifier = "^\\s*\\,\\s*stic\\s*$";

    static async run(data) {
        console.log('STICKER COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
        const has_quoted_media = data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage || data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;
        if (!has_upload_media && !has_quoted_media) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Burro burro! Você precisa enviar uma imagem ou gif para fazer um sticker! 🤦‍♂️'},
                {quoted: data, ephemeralExpiration: exp}
            );
            return;
        }

        try {
            const buffer = await downloadMediaMessage(data);
            console.log('BUFFER', buffer);
            if (buffer) {
                const sticker_buffer = await sharp(buffer)
                    .resize(512, 512, {
                        fit: sharp.fit.cover,
                        position: sharp.strategy.entropy
                    })
                    .webp({ quality: 50 })
                    .toBuffer();

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {sticker: sticker_buffer},
                    {quoted: data, ephemeralExpiration: exp}
                );
            }
        } catch (error) {
            console.error('ERROR STICKER COMMAND', error);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui criar a figurinha! 😔`},
                {quoted: data, ephemeralExpiration: exp}
            );
        }
    }
}