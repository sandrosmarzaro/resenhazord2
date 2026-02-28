import type { CommandData } from '../types/command.js';
import type { Message } from '../types/message.js';
import Command from './Command.js';
import AxiosClient from '../infra/AxiosClient.js';

interface VerseData {
  book: { name: string };
  chapter: number;
  number: number;
  text: string;
}

interface BookData {
  name: string;
  abbrev?: { pt: string };
}

export default class BibliaCommand extends Command {
  readonly regexIdentifier =
    '^\\s*,\\s*b.blia\\s*(?:pt|en)?\\s*(?:nvi|ra|acf|kjv|bbe|apee|rvr)?\\s*(?:.*\\s*\\d{1,3}\\s*:\\s*\\d{1,3}\\s*(?:-\\s*\\d{1,3})?)?$';
  readonly menuDescription = 'Comando complexo. Use *,menu biblia* para detalhes.';

  async run(data: CommandData): Promise<Message[]> {
    const has_verse = data.text.match(/.+\s*\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?/);
    const version = data.text.match(/\b(nvi|ra|acf|kjv|bbe|apee|rvr)\b/i) || 'nvi';
    const token = process.env.BIBLIA_TOKEN;
    const headers = {
      Authorization: `Bearer ${token}`,
    };

    const base_url = `https://www.abibliadigital.com.br/api`;
    let url;
    if (!has_verse) {
      url = `${base_url}/verses/${version}/random`;

      const response = await AxiosClient.get<VerseData>(url, { headers });
      return [this.build_verse(data, response.data)];
    }

    const rest_command = data.text
      .replace(/\s*,\s*b.blia\s*/, '')
      .replace(/(pt|en)/, '')
      .replace(/(nvi|ra|acf|kjv|bbe|apee|rvr)/, '')
      .replace(/\d{1,3}\s*:\s*\d{1,3}\s*(?:-\s*\d{1,3})?/, '')
      .trim();

    if (!rest_command || rest_command.match(/^\s*$/)) {
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: 'Por favor, digite o nome do livro da bíblia... 😔' },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    const book = rest_command;
    const chapter = data.text.match(/\d{1,3}:/)![0].replace(':', '');
    const has_range = data.text.match(/-\s*\d{1,3}/);
    const number = has_range
      ? data.text
          .match(/\d{1,3}\s*-\s*\d{1,3}/)![0]
          .split('-')
          .map((n) => n.trim())
      : data.text.match(/:\s*\d{1,3}/)![0].replace(':', '');

    const booksResponse = await AxiosClient.get<BookData[]>(`${base_url}/books`, { headers });
    const books = booksResponse.data;

    const abbrev = books.find((b) => b.name.toLowerCase() === book.toLowerCase())?.abbrev?.pt;
    if (!abbrev) {
      const book_names = books.map((b) => `- ${b.name}`).join('\n');
      let text = 'Não consegui encontrar o livro que você digitou... 😔';
      text += '\n\n📚 *Livros Disponíveis* 📚\n';
      text += book_names;
      return [
        {
          jid: data.key.remoteJid!,
          content: { text: text },
          options: { quoted: data, ephemeralExpiration: data.expiration },
        },
      ];
    }

    if (!has_range) {
      url = `${base_url}/verses/${version}/${abbrev}/${chapter}/${number}`;

      const verseResponse = await AxiosClient.get<VerseData>(url, { headers });
      return [this.build_verse(data, verseResponse.data)];
    }
    const [start, end] = number as string[];
    const verses: string[] = [];
    for (let i = parseInt(start); i <= parseInt(end); i++) {
      const verseUrl = `${base_url}/verses/${version}/${abbrev}/${chapter}/${i}`;
      const verseResponse = await AxiosClient.get<VerseData>(verseUrl, { headers });
      verses.push(`> ${verseResponse.data.text}`);
    }
    const text = `*${book} ${chapter}:${start}-${end}*\n\n${verses.join('\n')}`;
    return [
      {
        jid: data.key.remoteJid!,
        content: { text: text },
        options: { quoted: data, ephemeralExpiration: data.expiration },
      },
    ];
  }

  private build_verse(data: CommandData, verse: VerseData): Message {
    return {
      jid: data.key.remoteJid!,
      content: { text: `*${verse.book.name} ${verse.chapter}:${verse.number}*\n\n> ${verse.text}` },
      options: { quoted: data, ephemeralExpiration: data.expiration },
    };
  }
}
