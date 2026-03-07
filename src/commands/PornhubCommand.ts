import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { PornHub } from 'pornhub.js';
import m3u8ToMp4 from 'm3u8-to-mp4';
import Reply from '../builders/Reply.js';

export default class PornhubCommand extends Command {
  readonly config: CommandConfig = { name: 'pornhub' };
  readonly menuDescription = 'Receba um vídeo aleatório do Pornhub.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
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
          Reply.to(data).text('Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'),
        ];
      }
    } while (!has_240p);

    const converter = new m3u8ToMp4();
    await converter.setInputFile(m3u8_url).setOutputFile('../../public/videos/pornhub.mp4').start();

    const caption = `🔞 *${video.title || 'Aqui está seu vídeo 🤤'}* 🔞`;
    return [Reply.to(data).video('../../public/videos/pornhub.mp4', caption)];
  }
}
