import type { CommandData } from '../types/command.js';
import type { WAMessage } from '@whiskeysockets/baileys';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import Reply from '../builders/Reply.js';
import { Sentry } from '../infra/Sentry.js';
import sharp from 'sharp';
import pino from 'pino';

export default class ExtrairCommand extends Command {
  readonly config: CommandConfig = {
    name: 'extrair',
    category: 'download',
  };
  readonly menuDescription = 'Extraia a imagem ou GIF original de um sticker.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const quotedSticker =
      data.message?.extendedTextMessage?.contextInfo?.quotedMessage?.stickerMessage;

    if (!quotedSticker) {
      return [Reply.to(data).text('Responda a um sticker para extrair a imagem! 🤦‍♂️')];
    }

    const quotedMessage = data.message!.extendedTextMessage!.contextInfo!.quotedMessage!;
    const message: WAMessage = generateWAMessageFromContent(
      data.key.remoteJid!,
      quotedMessage as proto.IMessage,
      {
        userJid: data.key?.remoteJid?.includes('@g.us')
          ? data.key.participant!
          : data.key.remoteJid!,
      },
    );

    const buffer = await downloadMediaMessage(
      message,
      'buffer',
      {},
      {
        reuploadRequest: this.whatsapp!.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );

    try {
      if (quotedSticker.isAnimated) {
        const gifBuffer = await sharp(buffer as Buffer, { animated: true })
          .gif()
          .toBuffer();
        return [Reply.to(data).raw({ video: gifBuffer, gifPlayback: true, viewOnce: true })];
      } else {
        const pngBuffer = await sharp(buffer as Buffer)
          .png()
          .toBuffer();
        return [Reply.to(data).imageBuffer(pngBuffer)];
      }
    } catch (err) {
      Sentry.captureException(err, { extra: { isAnimated: quotedSticker.isAnimated } });
      return [Reply.to(data).text('Não consegui extrair a imagem do sticker 😅')];
    }
  }
}
