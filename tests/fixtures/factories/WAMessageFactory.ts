import { Factory } from 'fishery';
import type { WAMessage } from '@whiskeysockets/baileys';

interface WAMessageTransientParams {
  isGroup: boolean;
  hasImageMessage: boolean;
  hasVideoMessage: boolean;
  hasAudioMessage: boolean;
  hasStickerMessage: boolean;
  hasQuotedMessage: boolean;
  mentionedJids: string[];
}

export const WAMessageFactory = Factory.define<WAMessage, WAMessageTransientParams>(
  ({ transientParams, sequence }) => {
    const {
      isGroup = false,
      hasImageMessage = false,
      hasVideoMessage = false,
      hasAudioMessage = false,
      hasStickerMessage = false,
      hasQuotedMessage = false,
      mentionedJids = [],
    } = transientParams;

    const remoteJid = isGroup
      ? `${120363000000000000 + sequence}@g.us`
      : `5511${900000000 + sequence}@s.whatsapp.net`;

    const participant = isGroup ? `5511${900000000 + sequence}@s.whatsapp.net` : undefined;

    const message: WAMessage = {
      key: {
        remoteJid,
        fromMe: false,
        id: `MSG_${Date.now()}_${sequence}`,
        participant,
      },
      messageTimestamp: Math.floor(Date.now() / 1000),
      pushName: `User ${sequence}`,
      message: {},
    };

    if (hasImageMessage) {
      message.message = {
        imageMessage: {
          url: 'https://example.com/image.jpg',
          mimetype: 'image/jpeg',
          caption: '',
        },
      };
    } else if (hasVideoMessage) {
      message.message = {
        videoMessage: {
          url: 'https://example.com/video.mp4',
          mimetype: 'video/mp4',
          caption: '',
        },
      };
    } else if (hasAudioMessage) {
      message.message = {
        audioMessage: {
          url: 'https://example.com/audio.ogg',
          mimetype: 'audio/ogg',
        },
      };
    } else if (hasStickerMessage) {
      message.message = {
        stickerMessage: {
          url: 'https://example.com/sticker.webp',
          mimetype: 'image/webp',
        },
      };
    } else {
      message.message = {
        extendedTextMessage: {
          text: '',
          contextInfo: {
            mentionedJid: mentionedJids,
            quotedMessage: hasQuotedMessage
              ? {
                  conversation: 'quoted message',
                }
              : undefined,
          },
        },
      };
    }

    return message;
  },
);
