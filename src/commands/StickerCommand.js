import Resenhazord2 from "../models/Resenhazord2.js";
import { downloadMediaMessage } from "@whiskeysockets/baileys";
import { Sticker } from 'wa-sticker-formatter'
import { path as ffmpegPath } from '@ffmpeg-installer/ffmpeg';
import ffmpeg from 'fluent-ffmpeg';

export default class StickerCommand {

    static identifier = "^\\s*\\,\\s*stic\\s*(?:crop|full|circle|rounded)?\\s*$";

    static async run(data) {
        console.log('STICKER COMMAND');

        const exp = await Resenhazord2.socket.groupMetadata?.ephemeralDuration ||
                    data.message?.extendedTextMessage?.contextInfo?.expiration;

        const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
        const has_quoted_media = data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
                                data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;
        if (!has_upload_media && !has_quoted_media) {
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: 'Burro burro! Você precisa enviar uma imagem ou gif para fazer um sticker! 🤦‍♂️'},
                {quoted: data, ephemeralExpiration: exp}
            );
            return;
        }

        let rest_command = '';
        if (data.message?.imageMessage?.caption) {
            rest_command = data.message.imageMessage.caption.replace(/^\s*\,\s*stic\s*/, '');
        }
        if (data.message?.videoMessage?.caption) {
            rest_command = data.message.videoMessage.caption.replace(/^\s*\,\s*stic\s*/, '');
        }
        const type = rest_command.length > 0 ? rest_command : 'full';
        try {
            ffmpeg.setFfmpegPath(ffmpegPath);

            const buffer = await downloadMediaMessage(data, 'buffer', {});
            if (buffer) {
                const sticker = await new Sticker(buffer)
                    .setPack('Resenhazord2')
                    .setAuthor('Resenha')
                    .setType(type)
                    .setCategories(['Resenha', 'Bot'])
                    .setQuality(100)
                    .toBuffer();

                Resenhazord2.socket.sendMessage(
                    data.key.remoteJid,
                    {sticker: sticker},
                    {quoted: data, ephemeralExpiration: exp}
                );
            }
        }
        catch (error) {
            console.error('ERROR STICKER COMMAND', error);
            Resenhazord2.socket.sendMessage(
                data.key.remoteJid,
                {text: `Não consegui criar a figurinha! 😔`},
                {quoted: data, ephemeralExpiration: exp}
            );
        }
    }
}