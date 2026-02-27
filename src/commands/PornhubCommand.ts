import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { PornHub } from 'pornhub.js';
import m3u8ToMp4 from 'm3u8-to-mp4';

export default class PornhubCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*pornhub\\s*$';
  readonly menuDescription = 'Receba um vídeo aleatório do Pornhub.';

  async run(data: CommandData): Promise<Message[]> {
    const pornhub = new PornHub();

    let video;
    let has_240p = false;
    let tries = 0;
    let m3u8_url;
    do {
      video = await pornhub.randomVideo();
      if (!video.premium) {
        video.mediaDefinitions.forEach((media: { quality: unknown; videoUrl: string }) => {
          if (typeof media.quality === 'number' && media.quality === 240) {
            has_240p = media.quality === 240;
            m3u8_url = media.videoUrl;
          }
        });
      }

      if (!has_240p) {
        tries++;
      }
      if (tries > 500) {
        return [
          {
            jid: data.key.remoteJid!,
            content: { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
            options: { quoted: data, ephemeralExpiration: data.expiration },
          },
        ];
      }
    } while (!has_240p);

    const converter = new m3u8ToMp4();
    await converter.setInputFile(m3u8_url).setOutputFile('../../public/videos/pornhub.mp4').start();

    const caption = `🔞 *${video.title || 'Aqui está seu vídeo 🤤'}* 🔞`;
    return [
      {
        jid: data.key.remoteJid!,
        content: {
          viewOnce: true,
          caption: caption,
          video: { url: '../../public/videos/pornhub.mp4' },
        },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }
}
