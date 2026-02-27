import type { CommandData } from '../types/command.js';
import type { AnyMessageContent, WAMessage } from '@whiskeysockets/baileys';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { downloadMediaMessage, generateWAMessageFromContent, proto } from '@whiskeysockets/baileys';
import pino from 'pino';

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
  readonly regexIdentifier = '^\\s*\\,\\s*scarra\\s*$';
  readonly menuDescription = 'Baixe a mídia de visualização única marcada.';

  async run(data: CommandData): Promise<Message[]> {
    console.log(JSON.stringify(data, null, 2));
    const chat = data.key.remoteJid!;

    if (!chat.includes('g.us')) {
      return [
        {
          jid: chat,
          content: { text: 'Burro burro! Você só pode escarrar alguém em um grupo! 🤦‍♂️' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const quotedMessage = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
    const result = quotedMessage && findViewOnceMedia(quotedMessage);

    if (!result) {
      return [
        {
          jid: chat,
          content: {
            text: 'Burro burro! Você precisa marcar uma mensagem única pra eu escarrar! 🤦‍♂️',
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
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
        reuploadRequest: Resenhazord2.socket!.updateMediaMessage,
        logger: pino({ level: 'silent' }),
      },
    );

    const content: Record<string, unknown> = { [SEND_KEY[type]]: buffer };
    if (type !== 'audioMessage') {
      content.caption = (media.caption as string | undefined) || 'Escarrado! 😝';
    }

    return [
      {
        jid: chat,
        content: content as AnyMessageContent,
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
