import type { CommandData } from '../types/command.js';
import type { WAMessage } from '@whiskeysockets/baileys';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import { google } from 'googleapis';
import path from 'path';
import { createReadStream, promises as fsPromises } from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import pino from 'pino';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default class DriveCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*drive\\s*$';
  readonly menuDescription = 'Envie uma mídia para o Drive da Resenha.';

  async run(data: CommandData): Promise<Message[]> {
    const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
    const has_quoted_media =
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;

    if (!has_upload_media && !has_quoted_media) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Burro burro! Você precisa enviar uma mídia para botar no drive! 🤦‍♂️' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    let message: WAMessage;
    if (has_quoted_media) {
      const quoted_message = data.message!.extendedTextMessage!.contextInfo!.quotedMessage!;
      message = generateWAMessageFromContent(
        data.key.remoteJid!,
        quoted_message as proto.IMessage,
        {
          userJid: data.key?.remoteJid?.includes('@g.us')
            ? data.key.participant!
            : data.key.remoteJid!,
        },
      );
    } else {
      message = data as WAMessage;
    }

    const buffer = await downloadMediaMessage(
      message,
      'buffer',
      {},
      {
        reuploadRequest: Resenhazord2.socket!.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );

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

    return [
      {
        jid: data.key.remoteJid!,
        content: { text: `Mídia enviada com sucesso para o Drive da Resenha! 🐮🎣` },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
