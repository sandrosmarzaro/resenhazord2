import type { CommandData } from '../types/command.js';
import type { AnyMessageContent, WAMessage } from '@whiskeysockets/baileys';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import pino from 'pino';
import Reply from '../builders/Reply.js';

const MEDIA_TYPES = ['imageMessage', 'videoMessage', 'audioMessage'] as const;
type MediaType = (typeof MEDIA_TYPES)[number];

const WRAPPERS = ['viewOnceMessageV2', 'viewOnceMessageV2Extension', 'viewOnceMessage'] as const;

const SEND_KEY: Record<MediaType, string> = {
  imageMessage: 'image',
  videoMessage: 'video',
  audioMessage: 'audio',
};

type AnyMsg = Record<string, Record<string, unknown> | undefined>;

function findViewOnceMedia(
  message: proto.IMessage,
): { media: Record<string, unknown>; type: MediaType } | null {
  const msg = message as AnyMsg;
  for (const type of MEDIA_TYPES) {
    for (const wrapper of WRAPPERS) {
      const wrapperMsg = msg[wrapper];
      const inner = wrapperMsg?.['message'] as AnyMsg | undefined;
      const media = inner?.[type] as Record<string, unknown> | undefined;
      if (media) return { media, type };
    }
    const directMedia = msg[type];
    if (directMedia?.['viewOnce']) return { media: directMedia, type };
  }
  return null;
}

export default class ScarraCommand extends Command {
  readonly config: CommandConfig = { name: 'scarra', groupOnly: true, category: 'download' };
  readonly menuDescription = 'Baixe a mídia de visualização única marcada.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    const chat = data.key.remoteJid!;

    const quotedMessage = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
    const result = quotedMessage && findViewOnceMedia(quotedMessage);

    if (!result) {
      return [
        Reply.to(data).text(
          'Burro burro! Você precisa marcar uma mensagem única pra eu escarrar! 🤦‍♂️',
        ),
      ];
    }

    const { media, type } = result;

    const message = generateWAMessageFromContent(chat, quotedMessage as proto.IMessage, {
      userJid: data.key.participant || chat,
    });

    const buffer = await downloadMediaMessage(
      message as WAMessage,
      'buffer',
      {},
      {
        reuploadRequest: this.whatsapp!.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );

    const content: Record<string, unknown> = { [SEND_KEY[type]]: buffer };
    if (type !== 'audioMessage') {
      content.caption = (media.caption as string | undefined) || 'Escarrado! 😝';
    }

    return [Reply.to(data).raw(content as AnyMessageContent)];
  }
}
