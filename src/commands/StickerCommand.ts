import type { CommandData } from '../types/command.js';
import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import Reply from '../builders/Reply.js';
import { Sticker } from 'wa-sticker-formatter';
import { path as ffmpegPath } from '@ffmpeg-installer/ffmpeg';
import ffmpeg from 'fluent-ffmpeg';
import pino from 'pino';

export default class StickerCommand extends Command {
  readonly config: CommandConfig = {
    name: 'stic',
    options: [{ name: 'type', values: ['crop', 'full', 'circle', 'rounded'] }],
  };
  readonly menuDescription = 'Transforme sua imagem anexada em sticker.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const has_upload_media = data?.message?.imageMessage || data?.message?.videoMessage;
    const has_quoted_media =
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.imageMessage ||
      data?.message?.extendedTextMessage?.contextInfo?.quotedMessage?.videoMessage;
    if (!has_upload_media && !has_quoted_media) {
      return [
        Reply.to(data).text(
          'Burro burro! Você precisa enviar uma imagem ou gif para fazer um sticker! 🤦‍♂️',
        ),
      ];
    }

    const type = parsed.options.get('type') || 'full';

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
    ffmpeg.setFfmpegPath(ffmpegPath);

    const buffer = await downloadMediaMessage(
      message,
      'buffer',
      {},
      {
        reuploadRequest: this.whatsapp!.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );
    const sticker = await new Sticker(buffer)
      .setPack('Resenhazord2')
      .setAuthor('Resenha')
      .setType(type)
      .setCategories(['Resenha', 'Bot'])
      .setQuality(50)
      .build();
    return [Reply.to(data).sticker(sticker)];
  }
}
