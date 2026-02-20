import Resenhazord2 from "../models/Resenhazord2.js";
import { downloadMediaMessage, generateWAMessageFromContent } from "@whiskeysockets/baileys";

const MEDIA_TYPES = ['imageMessage', 'videoMessage', 'audioMessage'];
const WRAPPERS = ['viewOnceMessageV2', 'viewOnceMessageV2Extension', 'viewOnceMessage'];

const SEND_KEY = {
  imageMessage: 'image',
  videoMessage: 'video',
  audioMessage: 'audio',
};

function findViewOnceMedia(message) {
  for (const type of MEDIA_TYPES) {
    for (const wrapper of WRAPPERS) {
      const media = message[wrapper]?.message?.[type];
      if (media) return { media, type };
    }
    if (message[type]?.viewOnce) return { media: message[type], type };
  }
  return null;
}

export default class ScarraCommand {

  static identifier = "^\\s*\\,\\s*scarra\\s*$";

  static async run(data) {
    console.log(JSON.stringify(data, null, 2));
    const chat = data.key.remoteJid;

    if (!chat.includes('g.us')) {
      await Resenhazord2.socket.sendMessage(chat,
        { text: 'Burro burro! Você só pode escarrar alguém em um grupo! 🤦‍♂️' },
        { quoted: data, ephemeralExpiration: data.expiration }
      );
      return;
    }

    const quotedMessage = data.message?.extendedTextMessage?.contextInfo?.quotedMessage;
    const result = quotedMessage && findViewOnceMedia(quotedMessage);

    if (!result) {
      await Resenhazord2.socket.sendMessage(chat,
        { text: 'Burro burro! Você precisa marcar uma mensagem única pra eu escarrar! 🤦‍♂️' },
        { quoted: data, ephemeralExpiration: data.expiration }
      );
      return;
    }

    const { media, type } = result;

    try {
      const message = generateWAMessageFromContent(chat, quotedMessage, {
        userJid: data.key.participant || chat
      });

      const buffer = await downloadMediaMessage(message, 'buffer', {}, {
        reuploadRequest: await Resenhazord2.socket.updateMediaMessage
      });

      const content = { [SEND_KEY[type]]: buffer };
      if (type !== 'audioMessage') {
        content.caption = media.caption || 'Escarrado! 😝';
      }

      await Resenhazord2.socket.sendMessage(chat, content,
        { quoted: data, ephemeralExpiration: data.expiration }
      );
    } catch (error) {
      console.log(`ERROR SCARRA COMMAND\n${error}`);
      await Resenhazord2.socket.sendMessage(chat,
        { text: 'Não consegui escarrar! 😔' },
        { quoted: data, ephemeralExpiration: data.expiration }
      );
    }
  }
}
