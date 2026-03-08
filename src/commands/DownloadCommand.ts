import type { CommandData } from '../types/command.js';
import type { CommandConfig, ParsedCommand } from '../types/commandConfig.js';
import type { Message } from '../types/message.js';
import { ArgType } from '../types/commandConfig.js';
import Command from './Command.js';
import Reply from '../builders/Reply.js';
import YtDlpService from '../services/YtDlpService.js';
import { Sentry } from '../infra/Sentry.js';

export default class DownloadCommand extends Command {
  readonly config: CommandConfig = {
    name: 'dl',
    aliases: ['baixar'],
    flags: ['show', 'dm'],
    args: ArgType.Required,
    argsPattern: /https?:\/\/.+/,
    category: 'download',
  };
  readonly menuDescription = 'Baixe vídeos de qualquer URL (YouTube, Instagram, TikTok, etc.).';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    try {
      const { buffer, title } = await YtDlpService.download(parsed.rest);
      return [Reply.to(data).videoBuffer(buffer, title)];
    } catch (err) {
      Sentry.captureException(err, { extra: { url: parsed.rest } });
      console.error('[DownloadCommand] yt-dlp error:', err);
      return [Reply.to(data).text('Não consegui baixar esse vídeo 😅')];
    }
  }
}
