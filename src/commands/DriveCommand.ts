import type { CommandData } from '../types/command.js';
import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import Reply from '../builders/Reply.js';
import { google } from 'googleapis';
import path from 'path';
import { createReadStream, promises as fsPromises } from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import pino from 'pino';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default class DriveCommand extends Command {
  readonly config: CommandConfig = { name: 'drive' };
  readonly menuDescription = 'Envie uma mídia para o Drive da Resenha.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
    const has_quoted_media =
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;

    if (!has_upload_media && !has_quoted_media) {
      return [
        Reply.to(data).text('Burro burro! Você precisa enviar uma mídia para botar no drive! 🤦‍♂️'),
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
        reuploadRequest: this.whatsapp!.updateMediaMessage,
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

    return [Reply.to(data).text(`Mídia enviada com sucesso para o Drive da Resenha! 🐮🎣`)];
  }
}
