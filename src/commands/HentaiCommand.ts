import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
} from './Command.js';
import HentaiScraper from '../scrapers/HentaiScraper.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import type { HentaiGallery } from '../types/commands/hentai.js';

export default class HentaiCommand extends Command {
  readonly config: CommandConfig = {
    name: 'hentai',
    flags: ['dm', 'show'],
    category: 'aleatórias',
  };

  readonly menuDescription = 'Envia um hentai aleatório com informações do Hitomi.la.';

  protected async execute(data: CommandData, _parsed: ParsedCommand): Promise<Message[]> {
    let lastError: unknown;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const gallery = await HentaiScraper.getRandomGallery();
        const cover = await AxiosClient.getBuffer(gallery.coverUrl, {
          retries: 0,
          headers: gallery.coverHeaders,
        });
        return [Reply.to(data).imageBuffer(cover, HentaiCommand.buildCaption(gallery))];
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError;
  }

  private static buildCaption(g: HentaiGallery): string {
    const MAX_TAGS = 10;
    const japTitle =
      g.japaneseTitle && g.japaneseTitle !== g.title ? `\n🗾 _${g.japaneseTitle}_` : '';
    const artists = g.artists.length > 0 ? g.artists.join(', ') : '—';
    const groups = g.groups.length > 0 ? g.groups.join(', ') : '—';
    const shownTags = g.tags.slice(0, MAX_TAGS);
    const extraTags = g.tags.length - MAX_TAGS;
    const tagsStr =
      shownTags.length > 0
        ? shownTags.join(', ') + (extraTags > 0 ? ` (+${extraTags} more)` : '')
        : '—';

    return [
      `📖 *${g.title}*${japTitle}`,
      '',
      `✍️ ${artists}`,
      `👥 ${groups}`,
      `📚 ${g.type}`,
      `🌐 ${g.language}`,
      '',
      `🏷️ ${tagsStr}`,
      `📄 ${g.pages}`,
      `📅 ${g.date}`,
      '',
      `🔗 ${g.url}`,
    ].join('\n');
  }
}
