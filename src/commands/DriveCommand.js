import Resenhazord2 from '../models/Resenhazord2.js';
import { downloadMediaMessage, generateWAMessageFromContent } from "@whiskeysockets/baileys";
import { google } from 'googleapis';
import path from 'path';
import { createReadStream, promises as fsPromises } from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default class DriveCommand {

  static identifier = "^\\s*\\,\\s*drive\\s*$";

  static async run(data) {

    const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
    const has_quoted_media = data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
                             data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;

    if (!has_upload_media && !has_quoted_media) {
      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        {text: 'Burro burro! Você precisa enviar uma mídia para botar no drive! 🤦‍♂️'},
        {quoted: data, ephemeralExpiration: data.expiration}
      );
      return;
    }

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
      const buffer = await downloadMediaMessage(message, 'buffer', {}, {
        reuploadRequest: await Resenhazord2.socket.updateMediaMessage
      });

      const auth = new google.auth.GoogleAuth({
        keyFile: path.resolve(__dirname, '../auth/google_secret.json'),
        scopes: ['https://www.googleapis.com/auth/drive.file'],
      });

      const drive = google.drive({ version: 'v3', auth });

      const isImage = message.message?.imageMessage;
      const fileExtension = isImage ? '.jpg' : '.mp4';
      const fileName = `whatsapp_media_${Date.now()}${fileExtension}`;
      const mimeType = isImage ? 'image/jpeg' : 'video/mp4';

      const tempFilePath = path.join('/tmp', fileName);
      await fsPromises.writeFile(tempFilePath, buffer);

      const fileMetadata = {
        name: fileName,
        mimeType: mimeType,
      };

      const media = {
        mimeType: mimeType,
        body: createReadStream(tempFilePath),
      };

      await drive.files.create({
        requestBody: fileMetadata,
        media: media,
        fields: 'id',
      });

      await fsPromises.unlink(tempFilePath);

      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        {text: `Mídia enviada com sucesso para o Drive da Resenha! 🐮🎣`},
        {quoted: data, ephemeralExpiration: data.expiration}
      );
    }
    catch (error) {
      console.error('ERROR DRIVE COMMAND:', error);
      await Resenhazord2.socket.sendMessage(
        data.key.remoteJid,
        {text: 'Ocorreu um erro ao enviar a mídia para o Drive da Resenha ❌'},
        {quoted: data, ephemeralExpiration: data.expiration}
      );
    }
  }
}