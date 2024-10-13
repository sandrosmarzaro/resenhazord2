import Resenhazord2 from "../models/Resenhazord2.js";
import { downloadMediaMessage, generateWAMessageFromContent } from "@whiskeysockets/baileys";
import { Sticker } from 'wa-sticker-formatter'
import { path as ffmpegPath } from '@ffmpeg-installer/ffmpeg';
import ffmpeg from 'fluent-ffmpeg';

export default class StickerCommand {

    static identifier = "^\\s*\\,\\s*stic\\s*(?:crop|full|circle|rounded)?\\s*$";

    static async run(data) {

        const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
        const has_quoted_media = data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
                                data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;
        if (!has_upload_media && !has_quoted_media) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Burro burro! Você precisa enviar uma imagem ou gif para fazer um sticker! 🤦‍♂️'},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
            return;
        }

        const rest_command = data.text.replace(/^\s*\,\s*stic\s*/, '');
        const type = rest_command.length > 0 ? rest_command : 'full';

        let message;
        if (has_quoted_media) {
            const quoted_message = data.message.extendedTextMessage.contextInfo.quotedMessage;
            message = generateWAMessageFromContent(data.key.remoteJid, quoted_message, {
                userJid: data.key?.remoteJid?.includes('@g.us') ? data.key.participant : data.key.remoteJid
            });
        }
        else {
            message = data;
        }
        try {
            ffmpeg.setFfmpegPath(ffmpegPath);

            const buffer = await downloadMediaMessage(message, 'buffer', {},  {
                reuploadRequest: Resenhazord2.socket.updateMediaMessage
            });
            const sticker = await new Sticker(buffer)
                .setPack('Resenhazord2')
                .setAuthor('Resenha')
                .setType(type)
                .setCategories(['Resenha', 'Bot'])
                .setQuality(50)
                .build();
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {sticker},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
        catch (error) {
            console.log(`ERROR STICKER COMMAND\n${error}`);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui criar a figurinha! 😔`},
                {quoted: data, ephemeralExpiration: data.expiration}
            );
        }
    }
}