import type { CommandData } from '../types/command.js';
import type { AnyMessageContent } from '@whiskeysockets/baileys';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import { NSFW } from 'nsfwhub';
import pkg from 'darksadas-yt-pornhub-scrape';
const { phdl } = pkg;
import { NSFW_TAGS } from '../data/nsfwTags.js';

export default class PornoCommand extends Command {
  readonly regexIdentifier = '^\\s*\\,\\s*porno\\s*(?:ia)?\\s*(?:show)?\\s*(?:dm)?$';
  readonly menuDescription = 'Receba um porno aleatório real ou feito por IA.';

  async run(data: CommandData): Promise<Message[]> {
    const ia_activate = data.text.match(/ia/);
    if (ia_activate) {
      return await this.ia_porn(data);
    }
    return await this.real_porn(data);
  }

  private async ia_porn(data: CommandData): Promise<Message[]> {
    const nsfw = new NSFW();
    const tag = NSFW_TAGS[Math.floor(Math.random() * NSFW_TAGS.length)];
    const porn = await nsfw.fetch(tag);
    const content: Record<string, unknown> = {
      viewOnce: !data.text.match(/show/),
      caption: 'Aqui está seu vídeo 🤤',
    };

    if (porn?.image?.url?.endsWith('.mp4')) {
      content.video = { url: porn.image.url };
    } else if (porn?.image?.url?.endsWith('.gif')) {
      content.image = { url: porn.image.url };
      content.gifPlayback = true;
    } else {
      content.image = { url: porn.image.url };
    }

    let chat_id: string = data.key.remoteJid!;
    const DM_FLAG_ACTIVE = data.text.match(/dm/);
    if (DM_FLAG_ACTIVE && data.key.participant) {
      chat_id = data.key.participant;
    }
    return [
      {
        jid: chat_id,
        content: content as AnyMessageContent,
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }

  private async real_porn(data: CommandData): Promise<Message[]> {
    try {
      const results = (await phdl('https://pt.pornhub.com/random')) as {
        format: Array<{ download_url: string }>;
        video_title: string;
      };
      let chat_id: string = data.key.remoteJid!;
      const DM_FLAG_ACTIVE = data.text.match(/dm/);
      if (DM_FLAG_ACTIVE && data.key.participant) {
        chat_id = data.key.participant;
      }
      return [
        {
          jid: chat_id,
          content: {
            video: {
              url: results.format[0].download_url,
            },
            caption: results.video_title,
            viewOnce: !data.text.match(/show/),
          },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    } catch (error) {
      console.log(`ERROR PORN COMMAND\n${error}`);
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }
  }
}
