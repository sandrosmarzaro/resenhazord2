import Command, {
  type CommandData,
  type CommandConfig,
  type ParsedCommand,
  type Message,
  ArgType,
} from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';
import Reply from '../builders/Reply.js';
import { torahBooks, type TorahBook } from '../data/torahBooks.js';
import type { SefariaResponse } from '../types/commands/sefaria.js';

const BOOKS_LIST =
  'Versículo não encontrado. 😔\n\n' +
  '📚 *Livros da Torá* 📚\n' +
  '- Genesis (בראשית) — 50 capítulos\n' +
  '- Exodus (שמות) — 40 capítulos\n' +
  '- Leviticus (ויקרא) — 27 capítulos\n' +
  '- Numbers (במדבר) — 36 capítulos\n' +
  '- Deuteronomy (דברים) — 34 capítulos';

export default class TorahCommand extends Command {
  readonly config: CommandConfig = {
    name: 'torá',
    options: [{ name: 'lang', values: ['he', 'en'] }],
    args: ArgType.Optional,
    flags: ['dm', 'show'],
    category: 'aleatórias',
  };
  readonly menuDescription = 'Receba um versículo aleatório da Torá em hebraico e inglês.';

  protected async execute(data: CommandData, parsed: ParsedCommand): Promise<Message[]> {
    const rest = parsed.rest.trim();
    const lang = parsed.options.get('lang');

    let ref: string;
    if (!rest) {
      ref = this.randomRef();
    } else {
      const match = rest.match(/^(.+?)\s+(\d+):(\d+)$/);
      if (!match) {
        return [Reply.to(data).text(BOOKS_LIST)];
      }
      const [, bookName, chapter, verse] = match;
      ref = `${bookName}.${chapter}.${verse}`;
    }

    const url = `https://www.sefaria.org/api/texts/${ref}?context=0`;
    const response = await AxiosClient.get<SefariaResponse>(url);
    const payload = response.data;

    if (payload.error) {
      return [Reply.to(data).text(BOOKS_LIST)];
    }

    const en = payload.text.replace(/<[^>]*>/g, '').trim();
    const he = payload.he.replace(/<[^>]*>/g, '').trim();

    return [this.buildReply(data, payload.ref, payload.heTitle, he, en, lang)];
  }

  private randomRef(): string {
    const book = torahBooks[Math.floor(Math.random() * torahBooks.length)] as TorahBook;
    const chapterIdx = Math.floor(Math.random() * book.chapters.length);
    const verse = Math.floor(Math.random() * book.chapters[chapterIdx]) + 1;
    return `${book.name}.${chapterIdx + 1}.${verse}`;
  }

  private buildReply(
    data: CommandData,
    ref: string,
    heTitle: string,
    he: string,
    en: string,
    lang: string | undefined,
  ): Message {
    const header = `*${ref} — ${heTitle}*`;
    let body: string;
    if (lang === 'he') {
      body = `> ${he}`;
    } else if (lang === 'en') {
      body = `> ${en}`;
    } else {
      body = `> ${he}\n\n> ${en}`;
    }
    return Reply.to(data).text(`${header}\n\n${body}`);
  }
}
