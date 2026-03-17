import type { AnyMessageContent } from '@whiskeysockets/baileys';
import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import { NSFW } from 'nsfwhub';
import { NSFW_TAGS } from '../data/nsfwTags.js';
import XVideosScraper from '../scrapers/XVideosScraper.js';
import Reply from '../builders/Reply.js';

export default class PornoCommand extends Command {
  readonly config: CommandConfig = {
    name: 'porno',
    flags: ['ia', 'show', 'dm'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba um porno aleatório real ou feito por IA.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    if (parsed.flags.has('ia')) {
      return await this.ia_porn(data);
    }
    return await this.real_porn(data);
  }

  private async ia_porn(data: CommandData): Promise<Message[]> {
    const nsfw = new NSFW();
    const tag = NSFW_TAGS[Math.floor(Math.random() * NSFW_TAGS.length)];
    const porn = await nsfw.fetch(tag);
    const content: Record<string, unknown> = {
      viewOnce: true,
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

    return [Reply.to(data).raw(content as AnyMessageContent)];
  }

  private async real_porn(data: CommandData): Promise<Message[]> {
    try {
      const result = await XVideosScraper.getRandomVideo();
      return [Reply.to(data).video(result.videoUrl, result.title)];
    } catch (error) {
      console.log(`ERROR PORN COMMAND\n${error}`);
      return [
        Reply.to(data).text('Não consegui baixar seu vídeo, vai ter que ficar molhadinho 🥶'),
      ];
    }
  }
}
