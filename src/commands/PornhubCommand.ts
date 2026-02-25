import type { CommandData } from '../types/command.js';
import Resenhazord2 from '../models/Resenhazord2.js';
import { PornHub } from 'pornhub.js';
import m3u8ToMp4 from 'm3u8-to-mp4';

export default class PornhubCommand {
  static identifier: string = '^\\s*\\,\\s*pornhub\\s*$';

  static async run(data: CommandData): Promise<void> {
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
        await Resenhazord2.socket!.sendMessage(
          data.key.remoteJid!,
          { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
          { quoted: data, ephemeralExpiration: data.expiration },
        );
        return;
      }
    } while (!has_240p);

    const converter = new m3u8ToMp4();
    try {
      await converter
        .setInputFile(m3u8_url)
        .setOutputFile('../../public/videos/pornhub.mp4')
        .start();

      const caption = `🔞 *${video.title || 'Aqui está seu vídeo 🤤'}* 🔞`;
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        {
          viewOnce: true,
          caption: caption,
          video: { url: '../../public/videos/pornhub.mp4' },
        },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
    } catch (error) {
      console.log(`ERROR PORNHUB COMMAND\n${error}`);
      await Resenhazord2.socket!.sendMessage(
        data.key.remoteJid!,
        { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
        { quoted: data, ephemeralExpiration: data.expiration },
      );
      return;
    }
  }
}
