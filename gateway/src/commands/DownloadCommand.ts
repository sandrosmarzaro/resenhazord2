import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
  ArgType,
} from './Command.js';
import Reply from '../builders/Reply.js';
import YtDlpService from '../clients/YtDlpService.js';
import { Sentry } from '../infra/Sentry.js';

export default class DownloadCommand extends Command {
  readonly config: CommandConfig = {
    name: 'dl',
    aliases: ['baixar'],
    flags: ['show', 'dm'],
    args: ArgType.Required,
    argsPattern: /https?:\/\/\S+[\s\S]*/,
    category: 'download',
  };
  readonly menuDescription = 'Baixe vídeos de qualquer URL (YouTube, Instagram, TikTok, etc.).';

  private static readonly URL_REGEX = /https?:\/\/\S+/;

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const url = parsed.rest.match(DownloadCommand.URL_REGEX)?.[0] ?? parsed.rest;
    try {
      const { buffer, title } = await YtDlpService.download(url);
      return [Reply.to(data).videoBuffer(buffer, title)];
    } catch (err) {
      Sentry.captureException(err, { extra: { url } });
      console.error('[DownloadCommand] yt-dlp error:', err);
      return [Reply.to(data).text('Não consegui baixar esse vídeo 😅')];
    }
  }
}
